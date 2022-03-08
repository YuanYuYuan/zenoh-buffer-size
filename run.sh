#!/usr/bin/env bash

BUF_SIZE_LIST=(
    65536
    131072
    262144
    524288
    1048576
)

PAYLOAD_SIZE_LIST=(
    8
    16
    32
    64
    128
    256
    512
    1024
    2048
    4096
    8192
    16384
    32768
    65500
    128000
    256000
    512000
    1024000
    2048000
    4096000
)


function ctrl_c() {
    cleanup
    exit
}

function cleanup() {
    killall -9 z_pub_thr
    killall -9 z_sub_thr
}


NUMBER=1000
SAMPLES=1000

LOG_DIR="logs"
mkdir -p $LOG_DIR

cleanup

for PAYLOAD in ${PAYLOAD_SIZE_LIST[@]}; do
    nice -10 taskset -c 0,1 ./target/release/z_pub_thr --payload $PAYLOAD &
    sleep 1
    LOG_FILE="${LOG_DIR}/${PAYLOAD}.txt"
    echo $LOG_FILE
    for BUF_SIZE in ${BUF_SIZE_LIST[@]}; do
        USAGE_DIR="usages/${PAYLOAD}"
        mkdir -p $USAGE_DIR
        psrecord " \
            nice -10 taskset -c 2,3 \
            ./target/release/z_sub_thr \
                --number $NUMBER \
                --samples $SAMPLES \
                --disable-callback \
                --rx-buffer-size $BUF_SIZE >> $LOG_FILE
        " \
            --log ${USAGE_DIR}/${BUF_SIZE}.txt \
            --include-children
    done
    killall -9 z_pub_thr
done
