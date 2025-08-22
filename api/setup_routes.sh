#!/bin/bash
# Setup routing for API container to reach WireGuard network

# Add route to WireGuard subnet through the WireGuard container
ip route add 10.100.0.0/16 via 172.20.0.2 2>/dev/null || true

# Enable IP forwarding
echo 1 > /proc/sys/net/ipv4/ip_forward

echo "Routes configured for WireGuard network access"