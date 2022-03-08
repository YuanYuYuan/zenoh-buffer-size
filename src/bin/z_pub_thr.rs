use clap::Parser;
use std::path::PathBuf;
use zenoh::{
    Result,
    prelude::ZFuture,
    config::{
        Config,
        EndPoint,
        whatami::WhatAmI
    },
    publication::CongestionControl,
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

    /// A configuration file
    #[clap(short, long)]
    config: Option<PathBuf>,

    /// Disable the multicast-based scouting mechanism
    #[clap(long)]
    no_multicast_scouting: bool,

    /// Payload size (bytes)
    #[clap(short, long)]
    payload: usize,

    /// RX buffer size (bytes), default: 64KiB
    #[clap(short, long, default_value = "65536")]
    rx_buffer_size: usize,
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
        payload,
        rx_buffer_size,
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

    let data: Vec<u8> = (0usize..payload)
        .map(|i| (i % 10) as u8)
        .collect();

    let session = zenoh::open(config).wait()?;
    let key_expr = session.declare_expr("/test/thr").wait()?;

    loop {
        session
            .put(&key_expr, data.clone())
            .congestion_control(CongestionControl::Block)
            .wait()?;
    }
}
