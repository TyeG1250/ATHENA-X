#!/bin/bash
# ATHENA-X Dashboard Startup Script

echo "============================================================"
echo "  ATHENA-X OmniView Dashboard"
echo "  Starting Real-Time Command Center..."
echo "============================================================"
echo ""

# Check if in correct directory
if [ ! -f "config/settings.yaml" ]; then
    echo "❌ Error: Must run from ATHENA-X root directory"
    exit 1
fi

# Start WebSocket Server in background
echo "🚀 Starting WebSocket Server (Port 8765)..."
python src/dashboard/websocket_server.py &
WS_PID=$!
echo "   PID: $WS_PID"

# Wait for server to start
sleep 2

# Check if dashboard/node_modules exists
if [ ! -d "dashboard/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd dashboard
    npm install
    cd ..
fi

# Start React Dashboard
echo "🎨 Starting React Dashboard (Port 3000)..."
cd dashboard
npm run dev &
REACT_PID=$!
echo "   PID: $REACT_PID"

echo ""
echo "============================================================"
echo "  ✅ Dashboard Started!"
echo "============================================================"
echo ""
echo "  WebSocket API:  http://localhost:8765"
echo "  Dashboard UI:   http://localhost:3000"
echo ""
echo "  WebSocket PID:  $WS_PID"
echo "  React PID:      $REACT_PID"
echo ""
echo "Press Ctrl+C to stop all services"
echo "============================================================"

# Wait for Ctrl+C
trap "echo ''; echo '🛑 Stopping services...'; kill $WS_PID $REACT_PID; exit" INT
wait
