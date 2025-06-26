// Chainlit Widget Integration Script
console.log("Chainlit copilot script loaded");

// Create the mountChainlitWidget function
window.mountChainlitWidget = function(config) {
    console.log("Mounting Chainlit widget with config:", config);
    
    const { chainlitServer, element, options = {} } = config;
    
    if (!element) {
        throw new Error("No element provided for mounting Chainlit widget");
    }
    
    // Create the widget HTML structure
    const widgetHtml = `
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
                    src="${chainlitServer || '/copilot'}"
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
    
    // Insert the widget HTML
    element.innerHTML = widgetHtml;
    
    // Add event listeners
    const toggle = element.querySelector('#chainlit-toggle');
    const widget = element.querySelector('#chainlit-widget');
    const closeBtn = element.querySelector('#chainlit-close');
    
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
    return { toggle, widget, toggleWidget };
};

// Handle Chainlit function calls
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

console.log("Chainlit copilot integration ready - mountChainlitWidget function available");
