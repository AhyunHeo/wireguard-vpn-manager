#!/usr/bin/env python3
"""
WireGuard Real-time Monitor
Provides a visual interface for monitoring WireGuard server status
"""

from flask import Flask, render_template, jsonify
import subprocess
import json
from datetime import datetime
import re

app = Flask(__name__)

def get_wireguard_status():
    """Get current WireGuard status"""
    try:
        # Run wg show command
        result = subprocess.run(
            ['docker', 'exec', 'wireguard-server', 'wg', 'show', 'wg0', 'dump'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return None
        
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            return None
        
        # Parse interface info (first line)
        interface_parts = lines[0].split('\t')
        interface = {
            'private_key': '(hidden)',
            'public_key': interface_parts[0] if len(interface_parts) > 0 else '',
            'listen_port': interface_parts[1] if len(interface_parts) > 1 else '',
            'fwmark': interface_parts[2] if len(interface_parts) > 2 else ''
        }
        
        # Parse peers (remaining lines)
        peers = []
        for line in lines[1:]:
            parts = line.split('\t')
            if len(parts) >= 8:
                peer = {
                    'public_key': parts[0],
                    'preshared_key': parts[1],
                    'endpoint': parts[2],
                    'allowed_ips': parts[3],
                    'latest_handshake': int(parts[4]) if parts[4] != '0' else 0,
                    'rx_bytes': int(parts[5]),
                    'tx_bytes': int(parts[6]),
                    'persistent_keepalive': parts[7]
                }
                
                # Format handshake time
                if peer['latest_handshake'] > 0:
                    handshake_time = datetime.fromtimestamp(peer['latest_handshake'])
                    peer['handshake_ago'] = (datetime.now() - handshake_time).total_seconds()
                    peer['handshake_formatted'] = handshake_time.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    peer['handshake_ago'] = None
                    peer['handshake_formatted'] = 'Never'
                
                # Determine connection status
                if peer['handshake_ago'] is not None and peer['handshake_ago'] < 180:  # 3 minutes
                    peer['status'] = 'connected'
                else:
                    peer['status'] = 'disconnected'
                
                peers.append(peer)
        
        return {
            'interface': interface,
            'peers': peers,
            'peer_count': len(peers),
            'connected_count': sum(1 for p in peers if p['status'] == 'connected')
        }
    
    except Exception as e:
        print(f"Error getting WireGuard status: {e}")
        return None

@app.route('/')
def index():
    """Main monitoring page"""
    return render_template('monitor.html')

@app.route('/api/status')
def api_status():
    """API endpoint for status updates"""
    status = get_wireguard_status()
    if status:
        return jsonify(status)
    else:
        return jsonify({'error': 'Failed to get status'}), 500

@app.route('/api/peer/<public_key>/remove', methods=['POST'])
def remove_peer(public_key):
    """Remove a peer"""
    try:
        result = subprocess.run(
            ['docker', 'exec', 'wireguard-server', 'wg', 'set', 'wg0', 
             'peer', public_key, 'remove'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return jsonify({'success': True})
        else:
            return jsonify({'error': result.stderr}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=51821, debug=False)