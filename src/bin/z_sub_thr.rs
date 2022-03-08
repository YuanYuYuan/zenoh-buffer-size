use clap::Parser;
use std::time::Instant;
use std::path::PathBuf;
use zenoh::{
    Result,
    prelude::*,
    config::{
        Config,
        EndPoint,
        whatami::WhatAmI
    },
};

#[derive(Parser)]
struct Args {
    /// The zenoh session mode (peer or client), default: peer
    #[clap(
        short,
        long,
        possible_values = ["peer", "client"],
        default_value = "peer"
    )]
    mode: WhatAmI,

    /// Endpoints to connect to
    #[clap(short = 'e', long, value_delimiter = ',')]
    connect: Option<Vec<EndPoint>>,

    /// Endpoints to listen on
    #[clap(short, long, value_delimiter = ',')]
    listen: Option<Vec<EndPoint>>,

    /// Number of throughput measurements
    #[clap(short, long, default_value = "10")]
    samples: u32,

    /// Number of messages in each throughput measurements
    #[clap(short, long, default_value = "100000")]
    number: u128,

    /// A configuration file
    #[clap(short, long)]
    config: Option<PathBuf>,

    /// Disable the multicast-based scouting mechanism
    #[clap(long)]
    no_multicast_scouting: bool,

    /// RX buffer size (bytes), default: 64KiB
    #[clap(short, long, default_value = "65536")]
    rx_buffer_size: usize,

    /// disable callback
    #[clap(short, long)]
    disable_callback: bool,
}


fn main() -> Result<()> {
    // initiate logging
    env_logger::init();

    let Args {
        mode,
        connect,
        listen,
        config,
        no_multicast_scouting,
        samples,
        number,
        rx_buffer_size,
        disable_callback,
    } = Args::parse();


    let config = {
        let mut config = if let Some(path) = config {
            Config::from_file(path)?
        } else {
            Config::default()
        };

        config.set_mode(Some(mode)).unwrap();

        if let Some(connect) = connect {
            config.connect.endpoints.extend(connect);
        }

        if let Some(listen) = listen {
            config.listen.endpoints.extend(listen);
        }

        if no_multicast_scouting {
            config.scouting.multicast.set_enabled(Some(false)).unwrap();
        }

        config.transport.link.set_rx_buffer_size(Some(rx_buffer_size)).unwrap();

        config
    };

    let session = zenoh::open(config).wait()?;

    let key_expr = session.declare_expr("/test/thr").wait()?;

    let mut count = 0u128;
    let mut start = Instant::now();

    let mut nm = 0;
    let mut average = 0.;

    if disable_callback {
        let sub = session
            .subscribe(&key_expr)
            .wait()?;
        while sub.recv().is_ok() {
            if count == 0 {
                start = Instant::now();
                count += 1;
            } else if count < number {
                count += 1;
            } else {
                let throughput = (number as f64) / start.elapsed().as_secs_f64();
                println!("{},{}", rx_buffer_size, throughput);
                nm += 1;
                count = 0;

                if nm >= samples {
                    sub.close().wait()?;
                    break;
                }
            }
        }
    } else {
        let _sub = session
            .subscribe(&key_expr)
            .callback(move |_sample| {
                if count == 0 {
                    start = Instant::now();
                    count += 1;
                } else if count < number {
                    count += 1;
                } else {
                    std::thread::sleep(std::time::Duration::from_millis(1));
                    average += print_stats(start, number);
                    nm += 1;
                    count = 0;

                    if nm >= samples {
                        average /= samples as f64;
                        println!("average msg/s: {:.6}", &average);
                        std::process::exit(0)
                    }
                }
            })
            .wait()?;
        std::thread::park();
    }
    Ok(())
}

fn print_stats(start: Instant, n: u128) -> f64 {
    let elapsed = start.elapsed().as_secs_f64();
    let throughput = (n as f64) / elapsed;
    println!("msg/s: {:.6}", &throughput);
    throughput
}
