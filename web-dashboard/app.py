#!/usr/bin/env python3
"""
WireGuard VPN Manager Web Dashboard
"""

from flask import Flask, render_template_string, jsonify, request, redirect, url_for
import requests
import json
from datetime import datetime
import secrets
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))

# API configuration
API_URL = os.getenv('API_URL', 'http://vpn-api:8090')
API_TOKEN = os.getenv('API_TOKEN', 'test-token-123')

# HTML Template
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WireGuard VPN Manager</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 32px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.15);
        }
        
        .header h1 {
            color: #1a202c;
            font-size: 32px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .header p {
            color: #718096;
            font-size: 16px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 24px;
            margin-bottom: 32px;
        }
        
        .stat-card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .stat-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.15);
        }
        
        .stat-card h3 {
            color: #718096;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .stat-card .value {
            font-size: 36px;
            font-weight: 700;
            color: #1a202c;
            line-height: 1;
        }
        
        .stat-card.total { border-top: 4px solid #805ad5; }
        .stat-card.connected { border-top: 4px solid #48bb78; }
        .stat-card.registered { border-top: 4px solid #4299e1; }
        .stat-card.disconnected { border-top: 4px solid #f56565; }
        
        .main-content {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 32px;
        }
        
        @media (max-width: 1024px) {
            .main-content {
                grid-template-columns: 1fr;
            }
        }
        
        .nodes-section {
            background: white;
            border-radius: 16px;
            padding: 32px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.15);
        }
        
        .actions-section {
            display: flex;
            flex-direction: column;
            gap: 24px;
        }
        
        .action-card {
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }
        
        .section-header h2 {
            color: #1a202c;
            font-size: 24px;
            font-weight: 600;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        .btn-success {
            background: #48bb78;
            color: white;
        }
        
        .btn-danger {
            background: #f56565;
            color: white;
        }
        
        .btn-warning {
            background: #ed8936;
            color: white;
        }
        
        .btn-group {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        thead {
            background: #f7fafc;
            border-bottom: 2px solid #e2e8f0;
        }
        
        th {
            text-align: left;
            padding: 12px 16px;
            color: #4a5568;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        td {
            padding: 16px;
            border-bottom: 1px solid #e2e8f0;
            color: #2d3748;
            font-size: 14px;
        }
        
        tbody tr:hover {
            background: #f7fafc;
        }
        
        .status-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .status-connected {
            background: #c6f6d5;
            color: #22543d;
        }
        
        .status-registered {
            background: #bee3f8;
            color: #2c5282;
        }
        
        .status-disconnected {
            background: #fed7d7;
            color: #742a2a;
        }
        
        .node-actions {
            display: flex;
            gap: 8px;
        }
        
        .node-actions button {
            padding: 6px 12px;
            font-size: 12px;
        }
        
        .qr-section {
            text-align: center;
        }
        
        .qr-section h3 {
            color: #1a202c;
            font-size: 18px;
            margin-bottom: 16px;
        }
        
        .qr-section p {
            color: #718096;
            margin-bottom: 20px;
            font-size: 14px;
        }
        
        #qr-display {
            margin-top: 20px;
        }
        
        .qr-code {
            background: white;
            padding: 20px;
            border-radius: 12px;
            display: inline-block;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        
        .loading {
            display: inline-block;
            width: 24px;
            height: 24px;
            border: 3px solid #e2e8f0;
            border-top-color: #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #718096;
        }
        
        .empty-state svg {
            width: 120px;
            height: 120px;
            margin-bottom: 20px;
            opacity: 0.3;
        }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        
        .modal.show {
            display: flex;
        }
        
        .modal-content {
            background: white;
            border-radius: 16px;
            padding: 32px;
            max-width: 600px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
        }
        
        .modal-header {
            margin-bottom: 24px;
        }
        
        .modal-header h3 {
            color: #1a202c;
            font-size: 24px;
        }
        
        .info-grid {
            display: grid;
            gap: 16px;
        }
        
        .info-item {
            display: grid;
            grid-template-columns: 140px 1fr;
            gap: 16px;
            padding: 12px;
            background: #f7fafc;
            border-radius: 8px;
        }
        
        .info-label {
            font-weight: 600;
            color: #4a5568;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .info-value {
            color: #2d3748;
            font-family: 'Courier New', monospace;
            word-break: break-all;
        }
        
        .close-modal {
            margin-top: 24px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 WireGuard VPN Manager</h1>
            <p>Central Management Dashboard for VPN Network</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card total">
                <h3>Total Nodes</h3>
                <div class="value" id="total-nodes">-</div>
            </div>
            <div class="stat-card connected">
                <h3>Connected</h3>
                <div class="value" id="connected-nodes">-</div>
            </div>
            <div class="stat-card registered">
                <h3>Registered</h3>
                <div class="value" id="registered-nodes">-</div>
            </div>
            <div class="stat-card disconnected">
                <h3>Disconnected</h3>
                <div class="value" id="disconnected-nodes">-</div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="nodes-section">
                <div class="section-header">
                    <h2>📡 Network Nodes</h2>
                    <div class="btn-group">
                        <button class="btn btn-primary" onclick="refreshNodes()">
                            🔄 Refresh
                        </button>
                        <button class="btn btn-success" onclick="testAllConnectivity()">
                            🔍 Test All
                        </button>
                        <button class="btn btn-warning" onclick="syncAllNodes()">
                            🔗 Sync All
                        </button>
                        <button class="btn btn-warning" onclick="refreshAllConfigs()">
                            🔧 Fix Configs
                        </button>
                    </div>
                </div>
                
                <div id="nodes-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Node ID</th>
                                <th>Type</th>
                                <th>VPN IP</th>
                                <th>Status</th>
                                <th>Created</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="nodes-body">
                            <tr>
                                <td colspan="6" style="text-align: center; padding: 40px;">
                                    <div class="loading"></div>
                                    <p style="margin-top: 16px;">Loading nodes...</p>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="actions-section">
                <div class="action-card">
                    <h3 style="margin-bottom: 16px; color: #1a202c;">🚀 Quick Deploy</h3>
                    <p style="color: #718096; margin-bottom: 20px; font-size: 14px;">
                        Generate QR code or installation link for easy node deployment
                    </p>
                    <button class="btn btn-primary" onclick="generateDeployment()" style="width: 100%;">
                        Generate Deployment Link
                    </button>
                    <div id="qr-display"></div>
                </div>
                
                <div class="action-card">
                    <h3 style="margin-bottom: 16px; color: #1a202c;">🛠️ Maintenance</h3>
                    <div class="btn-group" style="flex-direction: column;">
                        <button class="btn btn-warning" onclick="cleanupDisconnected()">
                            🗑️ Remove Disconnected Nodes
                        </button>
                        <button class="btn btn-danger" onclick="cleanupAll()">
                            ⚠️ Remove All Test Nodes
                        </button>
                    </div>
                </div>
                
                <div class="action-card">
                    <h3 style="margin-bottom: 16px; color: #1a202c;">📊 Network Info</h3>
                    <div class="info-grid">
                        <div class="info-item">
                            <span class="info-label">Network</span>
                            <span class="info-value">10.100.0.0/16</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Server</span>
                            <span class="info-value">192.168.0.68:51820</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <div id="nodeModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3>Node Details</h3>
            </div>
            <div id="modal-body"></div>
            <button class="btn btn-primary close-modal" onclick="closeModal()">Close</button>
        </div>
    </div>
    
    <script>
        let currentNodes = [];
        
        function formatDate(dateStr) {
            if (!dateStr) return '-';
            const date = new Date(dateStr);
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
        }
        
        function formatDateShort(dateStr) {
            if (!dateStr) return '-';
            const date = new Date(dateStr);
            const now = new Date();
            const diff = now - date;
            
            if (diff < 60000) return 'Just now';
            if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
            if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
            return date.toLocaleDateString();
        }
        
        async function loadNodes() {
            try {
                const response = await fetch('/api/nodes');
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.error || 'Failed to load nodes');
                }
                
                currentNodes = data.nodes || [];
                
                // Update stats
                document.getElementById('total-nodes').textContent = data.total || '0';
                document.getElementById('connected-nodes').textContent = data.connected || '0';
                document.getElementById('registered-nodes').textContent = data.registered || '0';
                document.getElementById('disconnected-nodes').textContent = data.disconnected || '0';
                
                // Update table
                const tbody = document.getElementById('nodes-body');
                
                if (currentNodes.length === 0) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="6" class="empty-state">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4M12 4v16"/>
                                </svg>
                                <h3 style="color: #4a5568; margin-bottom: 8px;">No nodes registered</h3>
                                <p style="font-size: 14px;">Deploy your first node to get started</p>
                            </td>
                        </tr>
                    `;
                    return;
                }
                
                tbody.innerHTML = currentNodes.map(node => `
                    <tr>
                        <td><strong>${node.node_id}</strong></td>
                        <td>${node.node_type}</td>
                        <td><code style="background: #f7fafc; padding: 4px 8px; border-radius: 4px;">${node.vpn_ip}</code></td>
                        <td>
                            <span class="status-badge status-${node.status}">
                                ${node.status}
                            </span>
                        </td>
                        <td title="${formatDate(node.created_at)}">${formatDateShort(node.created_at)}</td>
                        <td>
                            <div class="node-actions">
                                <button class="btn btn-primary" onclick="viewNode('${node.node_id}')">View</button>
                                <button class="btn btn-success" onclick="testNode('${node.node_id}')">Test</button>
                                <button class="btn btn-warning" onclick="syncNode('${node.node_id}')">Sync</button>
                                <button class="btn btn-danger" onclick="deleteNode('${node.node_id}')">Delete</button>
                            </div>
                        </td>
                    </tr>
                `).join('');
            } catch (error) {
                console.error('Error loading nodes:', error);
                document.getElementById('nodes-body').innerHTML = `
                    <tr>
                        <td colspan="6" style="text-align: center; padding: 40px; color: #f56565;">
                            Error loading nodes: ${error.message}
                        </td>
                    </tr>
                `;
            }
        }
        
        async function refreshNodes() {
            const btn = event.target;
            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span> Refreshing...';
            
            await loadNodes();
            
            btn.disabled = false;
            btn.innerHTML = '🔄 Refresh';
        }
        
        async function testAllConnectivity() {
            const btn = event.target;
            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span> Testing...';
            
            try {
                const response = await fetch('/api/test-connectivity', { method: 'POST' });
                const data = await response.json();
                
                if (!response.ok) throw new Error(data.error || 'Test failed');
                
                alert(`Connectivity Test Results:\\n\\nTested: ${data.tested} nodes\\nConnected: ${data.connected} nodes\\nDisconnected: ${data.tested - data.connected} nodes`);
                await loadNodes();
            } catch (error) {
                alert('Error testing connectivity: ' + error.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = '🔍 Test All';
            }
        }
        
        async function testNode(nodeId) {
            try {
                const response = await fetch(`/api/node/${nodeId}/test`, { method: 'POST' });
                const data = await response.json();
                
                if (!response.ok) throw new Error(data.error || 'Test failed');
                
                alert(`Node ${nodeId}:\\n${data.reachable ? '✅ Connected' : '❌ Unreachable'}`);
                await loadNodes();
            } catch (error) {
                alert('Error testing node: ' + error.message);
            }
        }
        
        async function viewNode(nodeId) {
            try {
                const response = await fetch(`/api/node/${nodeId}`);
                const data = await response.json();
                
                if (!response.ok) throw new Error(data.error || 'Failed to load node');
                
                const modalBody = document.getElementById('modal-body');
                modalBody.innerHTML = `
                    <div class="info-grid">
                        <div class="info-item">
                            <span class="info-label">Node ID</span>
                            <span class="info-value">${data.node_id}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Type</span>
                            <span class="info-value">${data.node_type}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Hostname</span>
                            <span class="info-value">${data.hostname}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">VPN IP</span>
                            <span class="info-value">${data.vpn_ip}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Public IP</span>
                            <span class="info-value">${data.public_ip || 'N/A'}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Status</span>
                            <span class="info-value">
                                <span class="status-badge status-${data.status}">${data.status}</span>
                            </span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">WireGuard Status</span>
                            <span class="info-value">${data.wireguard_status || 'Unknown'}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Created</span>
                            <span class="info-value">${formatDate(data.created_at)}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Last Seen</span>
                            <span class="info-value">${formatDate(data.updated_at)}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Config Exists</span>
                            <span class="info-value">${data.config_exists ? '✅ Yes' : '❌ No'}</span>
                        </div>
                    </div>
                `;
                
                document.getElementById('nodeModal').classList.add('show');
            } catch (error) {
                alert('Error viewing node: ' + error.message);
            }
        }
        
        function closeModal() {
            document.getElementById('nodeModal').classList.remove('show');
        }
        
        async function syncNode(nodeId) {
            try {
                const response = await fetch(`/api/node/${nodeId}/sync`, { method: 'POST' });
                const data = await response.json();
                
                if (!response.ok) throw new Error(data.error || 'Sync failed');
                
                alert(`Node ${nodeId} synced successfully`);
                await loadNodes();
            } catch (error) {
                alert('Error syncing node: ' + error.message);
            }
        }
        
        async function deleteNode(nodeId) {
            if (!confirm(`Are you sure you want to delete node ${nodeId}?\\n\\nThis action cannot be undone.`)) return;
            
            try {
                const response = await fetch(`/api/node/${nodeId}`, { method: 'DELETE' });
                const data = await response.json();
                
                if (!response.ok) throw new Error(data.error || 'Delete failed');
                
                await loadNodes();
            } catch (error) {
                alert('Error deleting node: ' + error.message);
            }
        }
        
        async function cleanupDisconnected() {
            const disconnectedCount = currentNodes.filter(n => n.status === 'disconnected').length;
            
            if (disconnectedCount === 0) {
                alert('No disconnected nodes to remove');
                return;
            }
            
            if (!confirm(`Remove ${disconnectedCount} disconnected nodes?\\n\\nThis will permanently delete all nodes that are not currently connected.`)) return;
            
            try {
                const response = await fetch('/api/cleanup-disconnected', { method: 'DELETE' });
                const data = await response.json();
                
                if (!response.ok) throw new Error(data.error || 'Cleanup failed');
                
                alert(`Successfully removed ${data.deleted} disconnected nodes`);
                await loadNodes();
            } catch (error) {
                alert('Error cleaning up: ' + error.message);
            }
        }
        
        async function cleanupAll() {
            if (!confirm('⚠️ WARNING ⚠️\\n\\nThis will remove ALL test nodes (auto-node-*).\\n\\nAre you absolutely sure?')) return;
            
            try {
                const testNodes = currentNodes.filter(n => n.node_id.startsWith('auto-node-'));
                
                if (testNodes.length === 0) {
                    alert('No test nodes to remove');
                    return;
                }
                
                const response = await fetch('/api/cleanup-test-nodes', { method: 'DELETE' });
                const data = await response.json();
                
                if (!response.ok) throw new Error(data.error || 'Cleanup failed');
                
                alert(`Successfully removed ${data.deleted} test nodes`);
                await loadNodes();
            } catch (error) {
                alert('Error cleaning up: ' + error.message);
            }
        }
        
        async function generateDeployment() {
            try {
                const response = await fetch('/api/generate-deployment');
                const data = await response.json();
                
                if (!response.ok) throw new Error(data.error || 'Generation failed');
                
                // Create QR code using qrcode.js or iframe
                const qrPageUrl = data.qr_url;
                document.getElementById('qr-display').innerHTML = `
                    <div style="margin-top: 24px;">
                        <div style="text-align: center; margin-bottom: 20px;">
                            <p style="color: #4a5568; font-size: 14px; margin-bottom: 12px;">
                                📱 Scan QR code with mobile or click link below
                            </p>
                            <a href="${qrPageUrl}" target="_blank" class="btn btn-primary">
                                🔗 Open QR Page
                            </a>
                        </div>
                        <div style="margin-top: 20px;">
                            <p style="color: #4a5568; font-size: 12px; margin-bottom: 8px;">Windows Installation URL:</p>
                            <div style="display: flex; gap: 8px; align-items: center;">
                                <input type="text" value="${data.install_url}" readonly 
                                       style="flex: 1; padding: 8px; border: 1px solid #e2e8f0; border-radius: 4px; font-family: monospace; font-size: 12px;">
                                <button class="btn btn-primary" onclick="navigator.clipboard.writeText('${data.install_url}')">
                                    📋 Copy
                                </button>
                            </div>
                        </div>
                        <div style="margin-top: 16px;">
                            <iframe src="${qrPageUrl}" style="width: 100%; height: 500px; border: 1px solid #e2e8f0; border-radius: 8px; background: white;"></iframe>
                        </div>
                    </div>
                `;
            } catch (error) {
                alert('Error generating deployment: ' + error.message);
            }
        }
        
        async function syncAllNodes() {
            const btn = event.target;
            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span> Syncing...';
            
            try {
                const response = await fetch('/api/sync-all', { method: 'POST' });
                const data = await response.json();
                
                if (!response.ok) throw new Error(data.error || 'Sync failed');
                
                alert(`Sync Complete:\n\nSynced: ${data.synced} nodes\nFailed: ${data.failed} nodes`);
                await loadNodes();
            } catch (error) {
                alert('Error syncing nodes: ' + error.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = '🔗 Sync All';
            }
        }
        
        async function refreshAllConfigs() {
            const btn = event.target;
            btn.disabled = true;
            btn.innerHTML = '<span class="loading"></span> Fixing...';
            
            try {
                const response = await fetch('/api/refresh-configs', { method: 'POST' });
                const data = await response.json();
                
                if (!response.ok) throw new Error(data.error || 'Refresh failed');
                
                alert(`Config Refresh Complete:\n\nUpdated: ${data.updated} nodes\nFailed: ${data.failed} nodes\n\nClients need to re-download and import the new configs.`);
                await loadNodes();
            } catch (error) {
                alert('Error refreshing configs: ' + error.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = '🔧 Fix Configs';
            }
        }
        
        // Auto-refresh every 30 seconds
        setInterval(loadNodes, 30000);
        
        // Load nodes on page load
        window.addEventListener('DOMContentLoaded', loadNodes);
        
        // Close modal on click outside
        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                e.target.classList.remove('show');
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/api/nodes')
def get_nodes():
    """Get all nodes from API"""
    try:
        headers = {'Authorization': f'Bearer {API_TOKEN}'}
        
        # Try the custom node manager endpoint first
        try:
            response = requests.get(f'{API_URL}/api/nodes/list', headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # Calculate statistics
                total = data.get('total', 0)
                nodes = data.get('nodes', [])
                
                connected = sum(1 for n in nodes if n.get('status') == 'connected')
                registered = sum(1 for n in nodes if n.get('status') == 'registered')
                disconnected = sum(1 for n in nodes if n.get('status') == 'disconnected')
                
                return jsonify({
                    'total': total,
                    'connected': connected,
                    'registered': registered,
                    'disconnected': disconnected,
                    'nodes': nodes
                })
        except:
            pass
        
        # Fallback to standard endpoint
        response = requests.get(f'{API_URL}/nodes', headers=headers, timeout=5)
        
        if response.status_code == 200:
            nodes = response.json()
            
            # Calculate statistics
            total = len(nodes)
            connected = sum(1 for n in nodes if n.get('connected', False))
            registered = sum(1 for n in nodes if n.get('status') == 'registered')
            disconnected = total - connected
            
            # Transform to expected format
            formatted_nodes = []
            for node in nodes:
                formatted_nodes.append({
                    'node_id': node.get('node_id'),
                    'node_type': node.get('node_type'),
                    'hostname': node.get('hostname'),
                    'vpn_ip': node.get('vpn_ip'),
                    'status': 'connected' if node.get('connected') else node.get('status', 'disconnected'),
                    'created_at': node.get('created_at'),
                    'updated_at': node.get('updated_at')
                })
            
            return jsonify({
                'total': total,
                'connected': connected,
                'registered': registered,
                'disconnected': disconnected,
                'nodes': formatted_nodes
            })
        else:
            return jsonify({'error': f'API returned {response.status_code}', 'nodes': []})
            
    except requests.exceptions.Timeout:
        return jsonify({'error': 'API timeout', 'nodes': []})
    except Exception as e:
        return jsonify({'error': str(e), 'nodes': []})

@app.route('/api/test-connectivity', methods=['POST'])
def test_connectivity():
    """Test connectivity to all nodes"""
    try:
        headers = {'Authorization': f'Bearer {API_TOKEN}'}
        response = requests.post(f'{API_URL}/api/nodes/test-connectivity', headers=headers, timeout=30)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API returned {response.status_code}'}), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/node/<node_id>/test', methods=['POST'])
def test_single_node(node_id):
    """Test connectivity to a single node"""
    try:
        headers = {'Authorization': f'Bearer {API_TOKEN}'}
        
        # First get node info from API
        response = requests.get(f'{API_URL}/api/nodes/{node_id}/status', headers=headers, timeout=10)
        
        if response.status_code != 200:
            # Fallback to standard endpoint
            response = requests.get(f'{API_URL}/nodes/{node_id}', headers=headers, timeout=10)
        
        if response.status_code == 200:
            node_data = response.json()
            vpn_ip = node_data.get('vpn_ip')
            
            # Test from API container (which has access to WireGuard network)
            test_response = requests.post(
                f'{API_URL}/api/nodes/test-single',
                json={'vpn_ip': vpn_ip, 'node_id': node_id},
                headers=headers,
                timeout=10
            )
            
            if test_response.status_code == 200:
                test_data = test_response.json()
                return jsonify({
                    'reachable': test_data.get('reachable', False),
                    'vpn_ip': vpn_ip,
                    'message': test_data.get('message', '')
                })
            else:
                # Fallback to local ping test
                import subprocess
                result = subprocess.run(
                    ["docker", "exec", "wireguard-server", "ping", "-c", "1", "-W", "2", vpn_ip],
                    capture_output=True,
                    text=True
                )
                
                reachable = result.returncode == 0
                
                return jsonify({
                    'reachable': reachable,
                    'vpn_ip': vpn_ip,
                    'ping_output': result.stdout if reachable else result.stderr
                })
        else:
            return jsonify({'error': f'Node not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cleanup-disconnected', methods=['DELETE'])
def cleanup_disconnected():
    """Remove all disconnected nodes"""
    try:
        headers = {'Authorization': f'Bearer {API_TOKEN}'}
        response = requests.delete(f'{API_URL}/api/nodes/cleanup-disconnected', headers=headers, timeout=10)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API returned {response.status_code}'}), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cleanup-test-nodes', methods=['DELETE'])
def cleanup_test_nodes():
    """Remove all test nodes (auto-node-*)"""
    try:
        headers = {'Authorization': f'Bearer {API_TOKEN}'}
        
        # First get all nodes
        response = requests.get(f'{API_URL}/api/nodes/list', headers=headers, timeout=5)
        if response.status_code != 200:
            return jsonify({'error': 'Failed to get nodes'}), 500
        
        nodes = response.json().get('nodes', [])
        test_node_ids = [n['node_id'] for n in nodes if n['node_id'].startswith('auto-node-')]
        
        if not test_node_ids:
            return jsonify({'deleted': 0, 'message': 'No test nodes found'})
        
        # Delete test nodes
        response = requests.delete(
            f'{API_URL}/api/nodes/cleanup',
            json={'node_ids': test_node_ids},
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API returned {response.status_code}'}), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/node/<node_id>', methods=['DELETE'])
def delete_node(node_id):
    """Delete specific node"""
    try:
        headers = {'Authorization': f'Bearer {API_TOKEN}'}
        
        # Try custom endpoint first
        response = requests.delete(
            f'{API_URL}/api/nodes/cleanup',
            json={'node_ids': [node_id]},
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        
        # Fallback to standard endpoint
        response = requests.delete(f'{API_URL}/nodes/{node_id}', headers=headers, timeout=10)
        
        if response.status_code == 200:
            return jsonify({'message': 'Node deleted successfully'})
        else:
            return jsonify({'error': f'API returned {response.status_code}'}), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/node/<node_id>')
def get_node(node_id):
    """Get specific node details"""
    try:
        headers = {'Authorization': f'Bearer {API_TOKEN}'}
        
        # Try custom endpoint first
        response = requests.get(f'{API_URL}/api/nodes/{node_id}/status', headers=headers, timeout=5)
        
        if response.status_code == 200:
            return jsonify(response.json())
        
        # Fallback to standard endpoint
        response = requests.get(f'{API_URL}/nodes/{node_id}', headers=headers, timeout=5)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API returned {response.status_code}'}), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-deployment')
def generate_deployment():
    """Generate deployment QR code and link"""
    try:
        # Generate a unique token
        token = secrets.token_hex(16)
        
        # Use the correct API server URL (port 8090)
        local_server_ip = os.getenv('LOCAL_SERVER_IP', '192.168.0.68')
        api_url = f"http://{local_server_ip}:8090"
        
        # Install URL for auto-installer
        install_url = f"{api_url}/install/{token}"
        
        # QR code page URL
        qr_url = f"{api_url}/vpn-qr?token={token}"
        
        return jsonify({
            'install_url': install_url,
            'qr_url': qr_url,
            'token': token,
            'direct_qr': f"{api_url}/api/qr/generate?url={install_url}"  # Direct QR image
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync-all', methods=['POST'])
def sync_all():
    """Sync all nodes to WireGuard server"""
    try:
        headers = {'Authorization': f'Bearer {API_TOKEN}'}
        response = requests.post(f'{API_URL}/api/nodes/sync-all', headers=headers, timeout=30)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API returned {response.status_code}'}), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/refresh-configs', methods=['POST'])
def refresh_configs():
    """Refresh all node configs with correct server IP"""
    try:
        headers = {'Authorization': f'Bearer {API_TOKEN}'}
        response = requests.post(f'{API_URL}/api/nodes/refresh-configs', headers=headers, timeout=30)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API returned {response.status_code}'}), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/node/<node_id>/sync', methods=['POST'])
def sync_node(node_id):
    """Sync specific node to WireGuard server"""
    try:
        headers = {'Authorization': f'Bearer {API_TOKEN}'}
        response = requests.post(f'{API_URL}/api/nodes/{node_id}/sync', headers=headers, timeout=10)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'API returned {response.status_code}'}), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("WireGuard VPN Manager - Web Dashboard")
    print("=" * 60)
    print(f"Dashboard URL: http://0.0.0.0:5000")
    print(f"API Backend: {API_URL}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False)