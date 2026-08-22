for i in $(seq 1 10); do
  cast send $TARGET_ADDR \
    "vote(bytes3,string,string)" "0x43494d" "SatoshiNakamoto" "" \
    --rpc-url $RPC_URL --private-key $PRIVATE_KEY
  echo "=== Vote $i done ==="
done