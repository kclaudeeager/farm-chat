#!/usr/bin/env python3
"""
Simple ThingsBoard with Chainlit Copilot
Renders ThingsBoard in an iframe with Chainlit widget mounted as floating copilot
"""

import os
import requests
import time
from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)

# Configuration
PORT = int(os.getenv('PORT', '9000'))
THINGSBOARD_HOST = os.getenv('THINGSBOARD_HOST', 'chainlit-groq-demo-thingsboard-1')
THINGSBOARD_PORT = os.getenv('THINGSBOARD_PORT', '9090')
THINGSBOARD_URL = f"http://{THINGSBOARD_HOST}:{THINGSBOARD_PORT}"

# ThingsBoard credentials
USERNAME = "tenant@thingsboard.org"
PASSWORD = "tenant"

# Global variable to store the JWT token
jwt_token = None
token_expiry = None

def get_thingsboard_url():
    """Get ThingsBoard URL - use relative path since we're behind Nginx"""
    return '/thingsboard/'

def get_chainlit_url():
    """Get Chainlit URL - use relative path since we're behind Nginx"""
    return '/copilot/'

def get_jwt_token():
    """Authenticate with ThingsBoard and get JWT token"""
    global jwt_token, token_expiry
    
    # Check if token is still valid (assuming 1 hour expiry)
    if jwt_token and token_expiry and time.time() < token_expiry:
        return jwt_token

    try:
        url = f"{THINGSBOARD_URL}/api/auth/login"
        payload = {"username": USERNAME, "password": PASSWORD}
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ Authenticated with ThingsBoard successfully")
            jwt_token = response.json().get("token")
            # Set expiry to 50 minutes from now (tokens typically last 1 hour)
            token_expiry = time.time() + (50 * 60)
            return jwt_token
        else:
            print(f"❌ Failed to authenticate with ThingsBoard: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error authenticating with ThingsBoard: {e}")
        return None

@app.route('/')
def dashboard():
    """Main dashboard with ThingsBoard iframe and Chainlit copilot"""
    # Get JWT token for ThingsBoard authentication
    token = get_jwt_token()
    
    if not token:
        return jsonify({'error': 'Failed to authenticate with ThingsBoard'}), 500
    
    thingsboard_url = get_thingsboard_url()
    chainlit_url = get_chainlit_url()
    
    return render_template('dashboard_with_copilot.html', 
                         thingsboard_url=thingsboard_url,
                         chainlit_url=chainlit_url,
                         jwt_token=token,
                         current_host=request.headers.get('Host', 'localhost'))

@app.route('/health')
def health():
    """Health check endpoint"""
    thingsboard_url = get_thingsboard_url()
    chainlit_url = get_chainlit_url()
    
    # Check ThingsBoard authentication
    token = get_jwt_token()
    auth_status = "authenticated" if token else "failed"
    
    return jsonify({
        'status': 'healthy', 
        'services': {
            'thingsboard': thingsboard_url,
            'chainlit': chainlit_url
        },
        'thingsboard_auth': auth_status
    })

@app.route('/copilot/index.js')
def copilot_script():
    """Serve the Chainlit copilot JavaScript file with mounting functionality"""
    script_content = '''
// Chainlit Copilot Widget Implementation
(function() {
    'use strict';

    // Event listener for form filling functionality
    window.addEventListener("chainlit-call-fn", (e) => {
        const { name, args, callback } = e.detail;
        
        // Handle general callbacks
        if (!name || name === "default") {
            callback("You sent: " + (args.msg || "no message"));
            return;
        }
        
        // Handle form filling functionality
        if (name === "formfill") {
            console.log("Form data received:", name, args);
            
            // Only try to access dash_clientside if it exists
            if (window.dash_clientside) {
                try {
                    dash_clientside.set_props("fieldA", { value: args.fieldA });
                    dash_clientside.set_props("fieldB", { value: args.fieldB });
                    dash_clientside.set_props("fieldC", { value: args.fieldC });
                    callback("Form data processed: " + args.fieldA + " " + args.fieldB + " " + args.fieldC);
                } catch (error) {
                    console.error("Error setting form props:", error);
                    callback("Error processing form data");
                }
            } else {
                console.warn("dash_clientside is not available");
                callback("Form processing not available");
            }
        }
    });

    // Main widget mounting function
    window.mountChainlitWidget = function(config) {
        console.log("Mounting Chainlit widget with config:", config);
        
        const container = config.element || document.getElementById('chainlit-container');
        if (!container) {
            throw new Error("Container element not found for Chainlit widget");
        }

        // Create the widget HTML structure
        container.innerHTML = `
            <div style="
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 1000;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            ">
                <!-- Toggle Button -->
                <div id="chainlit-toggle" style="
                    width: 60px;
                    height: 60px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
                    color: white;
                    font-size: 24px;
                    transition: all 0.3s ease;
                    border: none;
                ">🤖</div>
                
                <!-- Copilot Widget -->
                <div id="chainlit-widget" style="
                    position: absolute;
                    bottom: 70px;
                    right: 0;
                    width: 400px;
                    height: 600px;
                    background: white;
                    border-radius: 16px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
                    display: none;
                    overflow: hidden;
                    border: 1px solid #e5e5e5;
                ">
                    <!-- Header -->
                    <div style="
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 16px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    ">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 20px;">🤖</span>
                            <span style="font-weight: 600;">AI Farm Assistant</span>
                        </div>
                        <button id="chainlit-close" style="
                            background: none;
                            border: none;
                            color: white;
                            font-size: 18px;
                            cursor: pointer;
                            padding: 4px;
                            border-radius: 4px;
                            opacity: 0.8;
                            transition: opacity 0.2s;
                        ">✕</button>
                    </div>
                    
                    <!-- Chainlit iframe -->
                    <iframe 
                        src="${config.chainlitServer || '/copilot'}"
                        style="
                            width: 100%;
                            height: calc(100% - 60px);
                            border: none;
                            background: white;
                        "
                        allow="microphone; camera; clipboard-read; clipboard-write">
                    </iframe>
                </div>
            </div>
        `;

        // Add event listeners for the widget
        const toggle = document.getElementById('chainlit-toggle');
        const widget = document.getElementById('chainlit-widget');
        const closeBtn = document.getElementById('chainlit-close');
        
        let isOpen = false;
        
        function toggleWidget() {
            isOpen = !isOpen;
            if (isOpen) {
                widget.style.display = 'block';
                toggle.style.transform = 'scale(0.9)';
                toggle.innerHTML = '💬';
            } else {
                widget.style.display = 'none';
                toggle.style.transform = 'scale(1)';
                toggle.innerHTML = '🤖';
            }
        }
        
        toggle.addEventListener('click', toggleWidget);
        closeBtn.addEventListener('click', toggleWidget);
        
        // Hover effects
        toggle.addEventListener('mouseenter', function() {
            this.style.transform = isOpen ? 'scale(0.95)' : 'scale(1.05)';
            this.style.boxShadow = '0 6px 25px rgba(102, 126, 234, 0.6)';
        });
        
        toggle.addEventListener('mouseleave', function() {
            this.style.transform = isOpen ? 'scale(0.9)' : 'scale(1)';
            this.style.boxShadow = '0 4px 20px rgba(102, 126, 234, 0.4)';
        });

        console.log("Chainlit widget mounted successfully");
        return {
            toggle: toggleWidget,
            isOpen: () => isOpen
        };
    };

    console.log("Chainlit copilot script loaded - mountChainlitWidget function available");

})();
'''
    
    from flask import Response
    return Response(script_content, mimetype='application/javascript')

if __name__ == '__main__':
    print(f"🌾 Starting ThingsBoard with AI Copilot on port {PORT}")
    print(f"🏭 ThingsBoard: {get_thingsboard_url()}")
    print(f"🤖 Chainlit Copilot: {get_chainlit_url()}")
    print(f"🔗 ThingsBoard Backend: {THINGSBOARD_URL}")
    
    # Test authentication on startup
    token = get_jwt_token()
    if token:
        print("🔐 ThingsBoard authentication successful")
    else:
        print("⚠️  ThingsBoard authentication failed - check credentials")
    
    app.run(host='0.0.0.0', port=PORT, debug=True)
