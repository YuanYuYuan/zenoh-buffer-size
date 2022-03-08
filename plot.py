#!/usr/bin/env python3

import pandas as pd
import plotly.express as px
import os
from glob import glob
from pathlib import Path
from tap import Tap
import plotly.graph_objects as go
from tqdm import tqdm

PAYLOAD_LIST = [
    8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768,
    65500, 128000, 256000, 512000, 1024000, 2048000, 4096000
]


class MyArgParser(Tap):
    # log dir
    log_dir: Path = Path('./logs')
    # usage dir
    usage_dir: Path = Path('./usages')
    # output dir
    out_dir: Path = Path('./plots')


def load_single_throughput(file_path: Path) -> pd.DataFrame:
    data = pd.read_csv(file_path)
    data.columns = ['rx_buf_size', 'throughput']
    data['rx_buf_size'] = data['rx_buf_size'].map({
        65536: 64,
        131072: 128,
        262144: 256,
        524288: 512,
        1048576: 1024
    })
    data['payload'] = int(file_path.stem)
    return data


def load_throughput(dir: Path) -> pd.DataFrame:
    data = pd.concat([
        load_single_throughput(Path(f))
        for f in glob(os.path.join(dir, '*.txt'))
    ])
    data = data \
        .groupby(['rx_buf_size', 'payload'], as_index=False) \
        .agg({'throughput': ['mean', 'std']})
    data.columns = ['rx_buf_size', 'payload', 'mean', 'std']
    return data


def load_single_usage(file: Path, payload: int) -> pd.DataFrame:
    rx_buf_size = int(file.stem)
    data = pd.read_csv(
        file,
        sep='\\s+',
        skiprows=1,
        names=['t', 'CPU', 'MEM', 'VMEM']
    )
    data['payload'] = payload
    data['rx_buf_size'] = rx_buf_size
    #  data['rx_buf_size'] = data['rx_buf_size'].map({
    #      65536: 64,
    #      131072: 128,
    #      262144: 256,
    #      524288: 512,
    #      1048576: 1024
    #  })
    data['MA_CPU'] = data['CPU'].rolling(30).mean()
    data['MA_MEM'] = data['MEM'].rolling(30).mean()
    return data


def load_usage(dir: Path) -> pd.DataFrame:
    usages = [
        load_single_usage(Path(file), int(Path(payload_dir).stem))
        for payload_dir in os.listdir(dir)
        for file in glob(os.path.join(dir, payload_dir, '*.txt'))
    ]
    usages.sort(key=lambda d: d['rx_buf_size'].unique())
    return pd.concat(usages)
    #  data = pd.concat([
    #      load_single_usage(Path(file), int(Path(payload_dir).stem))
    #      for payload_dir in os.listdir(dir)
    #      for file in glob(os.path.join(dir, payload_dir, '*.txt'))
    #  ])
    #  return data


def plot_mem_usage(usage: pd.DataFrame):
    output_dir = os.path.join(args.out_dir, 'usages/mem')
    os.makedirs(output_dir, exist_ok=True)
    for payload in tqdm(usage['payload'].unique()):
        fig = px.line(
            usage[usage['payload'] == payload],
            x='t',
            y='MA_MEM',
            color='rx_buf_size',
            labels={
                't': 'Time (sec)',
                'MA_MEM': 'Memory (MiB)',
                'rx_buf_size': 'RX buffer size (KiB)',
            },
        )
        fig.update_layout(
            title='Memory Usage, payload size (bytes): %d' % payload,
            #  xaxis={
            #      #  'range': [0, 30],
            #      'dtick': 1,
            #  },
            #  yaxis={
            #      'range': [0, 128],
            #      'dtick': 8,
            #  },
            legend={
                'y': 1.3,
                'x': 1.0
            }
        )
        fig.write_image(os.path.join(
            output_dir,
            '%07d.jpg' % payload
        ))


def plot_usage(usage: pd.DataFrame):
    output_dir = os.path.join(args.out_dir, 'usages')
    os.makedirs(output_dir, exist_ok=True)

    for payload in tqdm(usage['payload'].unique()):
        traces = []
        for (rx_buf_size, cpu_color, mem_color) in [
            [64, '#33ccff', '#ff3399'],
            [128, '#3333ff', '#ff3333'],
            [256, '#3333ff', '#ff3333'],
            [512, '#3333ff', '#ff3333'],
            [1024, '#3333ff', '#ff3333'],
        ]:
            idx = (usage['payload'] == payload) & (usage['rx_buf_size'] == rx_buf_size)
            traces += [
                go.Scatter(
                    x=usage[idx]['t'],
                    y=usage[idx]['MA_CPU'],
                    marker=dict(color=cpu_color),
                    name=str(rx_buf_size) + ': CPU',
                    yaxis='y1',
                ),
                go.Scatter(
                    x=usage[idx]['t'],
                    y=usage[idx]['MA_MEM'],
                    marker=dict(color=mem_color),
                    name=str(rx_buf_size) + ': Memory',
                    yaxis='y2',
                )
            ]

        layout = go.Layout(
            title='Payload size (bytes): %d' % payload,
            xaxis={
                'title': 'Time (sec)',
                'range': [0, 30],
                'dtick': 1,
            },
            yaxis={
                'title': 'CPU (%)',
                'range': [0, 100 * 2],
                'dtick': 20,
            },
            yaxis2={
                'title': 'Memory (MB)',
                'overlaying': 'y',
                'side': 'right',
                'range': [0, 128],
                'dtick': 8,
            },
            legend={
                'y': 1.3,
                'x': 0.92
            }
        )
        fig = go.Figure(
            data=traces,
            layout=layout
        )

        fig.write_image(os.path.join(
            output_dir,
            '%07d.jpg' % payload
        ))


args = MyArgParser().parse_args()
os.makedirs(args.out_dir, exist_ok=True)
#  data = load_throughput(args.log_dir)
usages = load_usage(args.usage_dir)
plot_mem_usage(usages)


#  fig = px.line(
#      data,
#      x='payload',
#      y='mean',
#      error_y='std',
#      color='rx_buf_size',
#      log_x=True,
#      #  log_y=True,
#      labels={
#          'rx_buf_size': 'RX buffer size (KiB)',
#          'payload': 'Payload size (bytes)',
#          'mean': 'Msg/sec',
#      },
#      title='Throughput Comparison'
#  )
#  fig.update_layout(
#      xaxis = dict(
#          tickmode = 'array',
#          tickvals = PAYLOAD_LIST,
#      )
#  )
#  file_name = os.path.join(args.out_dir, 'throughput-comparison')
#  fig.write_html(file_name + '.html')
#  fig.write_image(file_name + '.jpeg')
#  #  fig.show()
