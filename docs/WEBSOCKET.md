# WebSocket Integration Guide

## Overview

FinTradeAgent provides comprehensive WebSocket support for real-time updates during agent execution, trade management, and system monitoring. This enables a responsive user experience with live progress updates and instant notifications.

## WebSocket Architecture

### Connection Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│   Vue.js Client │◄──►│  FastAPI Server │◄──►│  Agent Services │
│                 │    │                 │    │                 │
│  - Auto-connect │    │  - Connection   │    │  - Progress     │
│  - Live updates │    │    management   │    │    tracking     │
│  - Error handle │    │  - Message      │    │  - Event        │
│  - Reconnect    │    │    broadcast    │    │    publishing   │
│                 │    │  - Health check │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
   WebSocket Client         WebSocket Server       Event Publishers
```

## WebSocket Endpoints

### Agent Execution WebSocket

**Endpoint**: `WS /api/agents/{portfolio_name}/ws`

**Purpose**: Real-time updates during agent execution processes.

**Connection URL**: `ws://localhost:8000/api/agents/{portfolio_name}/ws`

#### Connection Flow

```
1. Client connects to WebSocket endpoint
2. Server accepts connection and registers client
3. Client receives confirmation message
4. Server sends real-time updates during execution
5. Connection maintained with periodic heartbeats
6. Client disconnects or server closes on completion
```

### System Monitoring WebSocket

**Endpoint**: `WS /api/system/monitor`

**Purpose**: Real-time system health and performance metrics.

**Connection URL**: `ws://localhost:8000/api/system/monitor`

## Message Types and Formats

### Agent Execution Messages

#### 1. Connection Established

```json
{
  "type": "connection_established",
  "data": {
    "client_id": "client_123456",
    "portfolio_name": "Take-Private Arbitrage",
    "connected_at": "2026-02-11T14:00:00Z"
  }
}
```

#### 2. Execution Started

```json
{
  "type": "execution_started",
  "data": {
    "execution_id": "exec_789abc",
    "portfolio_name": "Take-Private Arbitrage",
    "started_at": "2026-02-11T14:00:00Z",
    "estimated_duration_seconds": 120,
    "user_guidance": "Focus on tech stocks today"
  }
}
```

#### 3. Data Collection Progress

```json
{
  "type": "data_collection",
  "data": {
    "execution_id": "exec_789abc",
    "stage": "market_data",
    "substage": "fetching_stock_prices",
    "progress": 0.35,
    "progress_text": "35%",
    "current_activity": "Fetching current prices for 8 holdings...",
    "details": {
      "completed_symbols": ["AAPL", "MSFT", "GOOGL"],
      "remaining_symbols": ["AMZN", "TSLA", "META", "NVDA", "NFLX"],
      "total_symbols": 8
    }
  }
}
```

#### 4. LLM Processing Updates

```json
{
  "type": "llm_processing",
  "data": {
    "execution_id": "exec_789abc",
    "stage": "generating_recommendations",
    "provider": "openai",
    "model": "gpt-4o",
    "progress": 0.75,
    "progress_text": "75%",
    "current_activity": "Analyzing market opportunities...",
    "token_usage": {
      "tokens_used": 6500,
      "estimated_total": 8500,
      "cost_so_far": 0.65,
      "estimated_total_cost": 0.85
    }
  }
}
```

#### 5. Recommendations Generated

```json
{
  "type": "recommendations_generated",
  "data": {
    "execution_id": "exec_789abc",
    "recommendations_count": 3,
    "summary": "Found 3 attractive arbitrage opportunities with average 12% spreads",
    "preview": [
      {
        "ticker": "VMW",
        "action": "BUY",
        "confidence": 0.85,
        "spread_pct": 15.1
      },
      {
        "ticker": "CTXS",
        "action": "SELL", 
        "confidence": 0.72,
        "reason": "Deal completion risk increased"
      }
    ]
  }
}
```

#### 6. Execution Completed

```json
{
  "type": "execution_completed",
  "data": {
    "execution_id": "exec_789abc",
    "status": "completed",
    "completed_at": "2026-02-11T14:02:30Z",
    "execution_time_seconds": 150,
    "summary": "Analysis complete. Generated 3 trade recommendations.",
    "statistics": {
      "total_tokens": 8750,
      "total_cost": 0.87,
      "data_sources_accessed": 12,
      "recommendations_generated": 3,
      "high_confidence_trades": 2
    },
    "next_actions": [
      "Review trade recommendations in the UI",
      "Execute approved trades",
      "Schedule next execution"
    ]
  }
}
```

#### 7. Execution Error

```json
{
  "type": "execution_error",
  "data": {
    "execution_id": "exec_789abc",
    "error_type": "llm_timeout",
    "error_code": "LLM_REQUEST_TIMEOUT",
    "message": "OpenAI request timed out after 30 seconds",
    "timestamp": "2026-02-11T14:01:45Z",
    "details": {
      "provider": "openai",
      "model": "gpt-4o",
      "request_id": "req_abc123",
      "tokens_used_before_error": 3200
    },
    "recovery_suggestions": [
      "Retry execution",
      "Try different LLM model",
      "Check network connectivity"
    ]
  }
}
```

### Trade Management Messages

#### 8. Trade Applied

```json
{
  "type": "trade_applied",
  "data": {
    "trade_id": "trade_456",
    "execution_result": {
      "status": "executed",
      "executed_price": 142.85,
      "shares": 25,
      "total_cost": 3571.25,
      "fees": 1.00,
      "executed_at": "2026-02-11T14:15:30Z"
    },
    "portfolio_impact": {
      "new_cash_balance": 6428.75,
      "new_total_value": 11387.50,
      "new_holding": {
        "ticker": "VMW",
        "total_shares": 25,
        "avg_price": 142.85
      }
    }
  }
}
```

#### 9. Trade Cancelled

```json
{
  "type": "trade_cancelled",
  "data": {
    "trade_id": "trade_789",
    "cancelled_at": "2026-02-11T14:20:00Z",
    "reason": "User cancelled",
    "user_note": "Market conditions changed"
  }
}
```

### System Monitoring Messages

#### 10. System Health Update

```json
{
  "type": "system_health",
  "data": {
    "timestamp": "2026-02-11T14:30:00Z",
    "overall_status": "healthy",
    "services": {
      "api": {
        "status": "healthy",
        "response_time_ms": 125,
        "requests_per_minute": 45
      },
      "database": {
        "status": "healthy",
        "query_time_ms": 8,
        "connection_pool_usage": 0.4
      },
      "cache": {
        "status": "healthy",
        "hit_rate": 0.89,
        "memory_usage_mb": 156
      }
    },
    "alerts": []
  }
}
```

## Backend WebSocket Implementation

### Connection Manager

```python
# backend/websocket/manager.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
import asyncio
from datetime import datetime

class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        # Portfolio-specific connections
        self.portfolio_connections: Dict[str, Set[WebSocket]] = {}
        # System monitoring connections
        self.system_connections: Set[WebSocket] = set()
        # Connection metadata
        self.connection_metadata: Dict[WebSocket, Dict] = {}
    
    async def connect_portfolio(self, websocket: WebSocket, portfolio_name: str):
        """Connect client to portfolio updates."""
        await websocket.accept()
        
        if portfolio_name not in self.portfolio_connections:
            self.portfolio_connections[portfolio_name] = set()
        
        self.portfolio_connections[portfolio_name].add(websocket)
        self.connection_metadata[websocket] = {
            "type": "portfolio",
            "portfolio_name": portfolio_name,
            "connected_at": datetime.utcnow(),
            "client_id": f"client_{id(websocket)}"
        }
        
        # Send connection confirmation
        await self.send_to_websocket(websocket, {
            "type": "connection_established",
            "data": {
                "client_id": self.connection_metadata[websocket]["client_id"],
                "portfolio_name": portfolio_name,
                "connected_at": datetime.utcnow().isoformat()
            }
        })
    
    async def connect_system(self, websocket: WebSocket):
        """Connect client to system monitoring."""
        await websocket.accept()
        self.system_connections.add(websocket)
        self.connection_metadata[websocket] = {
            "type": "system",
            "connected_at": datetime.utcnow(),
            "client_id": f"system_{id(websocket)}"
        }
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect client."""
        metadata = self.connection_metadata.get(websocket, {})
        
        if metadata.get("type") == "portfolio":
            portfolio_name = metadata.get("portfolio_name")
            if portfolio_name and portfolio_name in self.portfolio_connections:
                self.portfolio_connections[portfolio_name].discard(websocket)
                if not self.portfolio_connections[portfolio_name]:
                    del self.portfolio_connections[portfolio_name]
        
        elif metadata.get("type") == "system":
            self.system_connections.discard(websocket)
        
        self.connection_metadata.pop(websocket, None)
    
    async def send_to_portfolio(self, portfolio_name: str, message: dict):
        """Send message to all clients connected to a portfolio."""
        if portfolio_name not in self.portfolio_connections:
            return
        
        dead_connections = set()
        for websocket in self.portfolio_connections[portfolio_name].copy():
            try:
                await self.send_to_websocket(websocket, message)
            except Exception:
                dead_connections.add(websocket)
        
        # Clean up dead connections
        for websocket in dead_connections:
            self.disconnect(websocket)
    
    async def send_to_system_monitors(self, message: dict):
        """Send message to all system monitoring clients."""
        dead_connections = set()
        for websocket in self.system_connections.copy():
            try:
                await self.send_to_websocket(websocket, message)
            except Exception:
                dead_connections.add(websocket)
        
        # Clean up dead connections
        for websocket in dead_connections:
            self.disconnect(websocket)
    
    async def send_to_websocket(self, websocket: WebSocket, message: dict):
        """Send message to specific WebSocket."""
        await websocket.send_text(json.dumps(message, default=str))
    
    def get_connection_count(self, portfolio_name: str = None) -> int:
        """Get number of active connections."""
        if portfolio_name:
            return len(self.portfolio_connections.get(portfolio_name, set()))
        return sum(len(conns) for conns in self.portfolio_connections.values()) + len(self.system_connections)

# Global connection manager instance
connection_manager = ConnectionManager()
```

### WebSocket Router

```python
# backend/routers/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.websocket.manager import connection_manager
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/agents/{portfolio_name}/ws")
async def portfolio_websocket(websocket: WebSocket, portfolio_name: str):
    """WebSocket endpoint for portfolio-specific updates."""
    await connection_manager.connect_portfolio(websocket, portfolio_name)
    
    try:
        while True:
            # Keep connection alive by receiving heartbeat messages
            data = await websocket.receive_text()
            
            # Handle client messages if needed
            if data == "ping":
                await connection_manager.send_to_websocket(websocket, {
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from portfolio {portfolio_name}")
        connection_manager.disconnect(websocket)
    
    except Exception as e:
        logger.error(f"WebSocket error for portfolio {portfolio_name}: {e}")
        connection_manager.disconnect(websocket)

@router.websocket("/system/monitor")
async def system_websocket(websocket: WebSocket):
    """WebSocket endpoint for system monitoring."""
    await connection_manager.connect_system(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await connection_manager.send_to_websocket(websocket, {
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    except WebSocketDisconnect:
        logger.info("System monitor client disconnected")
        connection_manager.disconnect(websocket)
    
    except Exception as e:
        logger.error(f"System monitor WebSocket error: {e}")
        connection_manager.disconnect(websocket)
```

### Event Publishing

```python
# backend/services/event_publisher.py
from backend.websocket.manager import connection_manager
from typing import Dict, Any
import asyncio

class EventPublisher:
    """Publishes events to WebSocket clients."""
    
    @staticmethod
    async def publish_execution_started(portfolio_name: str, execution_id: str, user_guidance: str = None):
        """Publish execution started event."""
        message = {
            "type": "execution_started",
            "data": {
                "execution_id": execution_id,
                "portfolio_name": portfolio_name,
                "started_at": datetime.utcnow().isoformat(),
                "user_guidance": user_guidance
            }
        }
        await connection_manager.send_to_portfolio(portfolio_name, message)
    
    @staticmethod
    async def publish_progress_update(portfolio_name: str, execution_id: str, stage: str, progress: float, activity: str, details: Dict = None):
        """Publish progress update."""
        message = {
            "type": "data_collection" if "data" in stage.lower() else "llm_processing",
            "data": {
                "execution_id": execution_id,
                "stage": stage,
                "progress": progress,
                "progress_text": f"{int(progress * 100)}%",
                "current_activity": activity,
                "details": details or {}
            }
        }
        await connection_manager.send_to_portfolio(portfolio_name, message)
    
    @staticmethod
    async def publish_recommendations_generated(portfolio_name: str, execution_id: str, recommendations_count: int, summary: str, preview: list):
        """Publish recommendations generated event."""
        message = {
            "type": "recommendations_generated",
            "data": {
                "execution_id": execution_id,
                "recommendations_count": recommendations_count,
                "summary": summary,
                "preview": preview
            }
        }
        await connection_manager.send_to_portfolio(portfolio_name, message)
    
    @staticmethod
    async def publish_execution_completed(portfolio_name: str, execution_id: str, statistics: Dict, execution_time: int):
        """Publish execution completed event."""
        message = {
            "type": "execution_completed",
            "data": {
                "execution_id": execution_id,
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat(),
                "execution_time_seconds": execution_time,
                "statistics": statistics
            }
        }
        await connection_manager.send_to_portfolio(portfolio_name, message)
    
    @staticmethod
    async def publish_execution_error(portfolio_name: str, execution_id: str, error_type: str, error_message: str, details: Dict = None):
        """Publish execution error event."""
        message = {
            "type": "execution_error",
            "data": {
                "execution_id": execution_id,
                "error_type": error_type,
                "message": error_message,
                "timestamp": datetime.utcnow().isoformat(),
                "details": details or {}
            }
        }
        await connection_manager.send_to_portfolio(portfolio_name, message)

# Global event publisher
event_publisher = EventPublisher()
```

## Frontend WebSocket Integration

### WebSocket Service (Vue.js)

```javascript
// services/websocket.js
export class WebSocketService {
  constructor() {
    this.connections = new Map()
    this.reconnectAttempts = new Map()
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000 // Start with 1 second
    this.maxReconnectDelay = 30000 // Max 30 seconds
  }

  connectPortfolio(portfolioName, callbacks = {}) {
    const key = `portfolio:${portfolioName}`
    
    if (this.connections.has(key)) {
      return this.connections.get(key)
    }

    const wsUrl = `${this.getWebSocketUrl()}/api/agents/${portfolioName}/ws`
    const ws = new WebSocket(wsUrl)
    
    ws.onopen = () => {
      console.log(`WebSocket connected for portfolio: ${portfolioName}`)
      this.reconnectAttempts.set(key, 0)
      this.reconnectDelay = 1000
      callbacks.onOpen?.(portfolioName)
      
      // Start heartbeat
      this.startHeartbeat(ws)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        this.handleMessage(data, callbacks)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    ws.onclose = (event) => {
      console.log(`WebSocket closed for portfolio: ${portfolioName}`)
      this.connections.delete(key)
      callbacks.onClose?.(portfolioName, event)
      
      // Attempt reconnection if not intentionally closed
      if (event.code !== 1000 && event.code !== 1001) {
        this.scheduleReconnect(portfolioName, callbacks)
      }
    }

    ws.onerror = (error) => {
      console.error(`WebSocket error for portfolio ${portfolioName}:`, error)
      callbacks.onError?.(error)
    }

    this.connections.set(key, ws)
    return ws
  }

  connectSystemMonitor(callbacks = {}) {
    const key = 'system:monitor'
    
    if (this.connections.has(key)) {
      return this.connections.get(key)
    }

    const wsUrl = `${this.getWebSocketUrl()}/api/system/monitor`
    const ws = new WebSocket(wsUrl)
    
    ws.onopen = () => {
      console.log('System monitor WebSocket connected')
      callbacks.onOpen?.()
      this.startHeartbeat(ws)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        this.handleMessage(data, callbacks)
      } catch (error) {
        console.error('Failed to parse system monitor message:', error)
      }
    }

    ws.onclose = (event) => {
      console.log('System monitor WebSocket closed')
      this.connections.delete(key)
      callbacks.onClose?.(event)
      
      if (event.code !== 1000 && event.code !== 1001) {
        this.scheduleReconnect(null, callbacks, 'system:monitor')
      }
    }

    ws.onerror = (error) => {
      console.error('System monitor WebSocket error:', error)
      callbacks.onError?.(error)
    }

    this.connections.set(key, ws)
    return ws
  }

  handleMessage(data, callbacks) {
    const { type } = data
    
    // Route messages to appropriate handlers
    switch (type) {
      case 'execution_started':
        callbacks.onExecutionStarted?.(data.data)
        break
      case 'data_collection':
      case 'llm_processing':
        callbacks.onProgress?.(data.data)
        break
      case 'recommendations_generated':
        callbacks.onRecommendations?.(data.data)
        break
      case 'execution_completed':
        callbacks.onCompleted?.(data.data)
        break
      case 'execution_error':
        callbacks.onError?.(data.data)
        break
      case 'trade_applied':
        callbacks.onTradeApplied?.(data.data)
        break
      case 'system_health':
        callbacks.onSystemHealth?.(data.data)
        break
      case 'pong':
        // Heartbeat response
        break
      default:
        console.warn('Unknown WebSocket message type:', type)
    }
  }

  startHeartbeat(ws) {
    const interval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping')
      } else {
        clearInterval(interval)
      }
    }, 30000) // Ping every 30 seconds
  }

  scheduleReconnect(portfolioName, callbacks, key = null) {
    const connectionKey = key || `portfolio:${portfolioName}`
    const attempts = this.reconnectAttempts.get(connectionKey) || 0
    
    if (attempts >= this.maxReconnectAttempts) {
      console.error(`Max reconnection attempts reached for ${connectionKey}`)
      callbacks.onReconnectFailed?.()
      return
    }

    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, attempts),
      this.maxReconnectDelay
    )

    console.log(`Reconnecting ${connectionKey} in ${delay}ms (attempt ${attempts + 1})`)
    
    setTimeout(() => {
      this.reconnectAttempts.set(connectionKey, attempts + 1)
      
      if (key === 'system:monitor') {
        this.connectSystemMonitor(callbacks)
      } else {
        this.connectPortfolio(portfolioName, callbacks)
      }
    }, delay)
  }

  disconnect(portfolioName = null, type = 'portfolio') {
    const key = portfolioName ? `${type}:${portfolioName}` : 'system:monitor'
    const ws = this.connections.get(key)
    
    if (ws) {
      ws.close(1000, 'Client disconnect')
      this.connections.delete(key)
      this.reconnectAttempts.delete(key)
    }
  }

  disconnectAll() {
    this.connections.forEach((ws, key) => {
      ws.close(1000, 'Client shutdown')
    })
    this.connections.clear()
    this.reconnectAttempts.clear()
  }

  getWebSocketUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = process.env.NODE_ENV === 'development' 
      ? 'localhost:8000' 
      : window.location.host
    return `${protocol}//${host}`
  }
}

export const wsService = new WebSocketService()
```

### Vue Composable for WebSocket

```javascript
// composables/useWebSocket.js
import { ref, onMounted, onUnmounted } from 'vue'
import { wsService } from '@/services/websocket'

export function usePortfolioWebSocket(portfolioName) {
  const connected = ref(false)
  const executionStatus = ref(null)
  const progress = ref(0)
  const currentActivity = ref('')
  const recommendations = ref([])
  const error = ref(null)

  let ws = null

  const connect = () => {
    ws = wsService.connectPortfolio(portfolioName, {
      onOpen: () => {
        connected.value = true
        error.value = null
      },
      
      onClose: () => {
        connected.value = false
      },
      
      onExecutionStarted: (data) => {
        executionStatus.value = 'running'
        progress.value = 0
        currentActivity.value = 'Starting execution...'
        error.value = null
      },
      
      onProgress: (data) => {
        progress.value = data.progress || 0
        currentActivity.value = data.current_activity || 'Processing...'
      },
      
      onRecommendations: (data) => {
        recommendations.value = data.preview || []
        currentActivity.value = `Generated ${data.recommendations_count} recommendations`
      },
      
      onCompleted: (data) => {
        executionStatus.value = 'completed'
        progress.value = 1
        currentActivity.value = 'Execution completed'
      },
      
      onError: (data) => {
        executionStatus.value = 'error'
        error.value = data.message || 'Execution failed'
        currentActivity.value = 'Execution failed'
      },
      
      onReconnectFailed: () => {
        error.value = 'Failed to reconnect to server'
      }
    })
  }

  const disconnect = () => {
    if (ws) {
      wsService.disconnect(portfolioName)
      connected.value = false
    }
  }

  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    connected,
    executionStatus,
    progress,
    currentActivity,
    recommendations,
    error,
    connect,
    disconnect
  }
}

export function useSystemWebSocket() {
  const connected = ref(false)
  const systemHealth = ref(null)
  const error = ref(null)

  let ws = null

  const connect = () => {
    ws = wsService.connectSystemMonitor({
      onOpen: () => {
        connected.value = true
        error.value = null
      },
      
      onClose: () => {
        connected.value = false
      },
      
      onSystemHealth: (data) => {
        systemHealth.value = data
      },
      
      onError: (errorData) => {
        error.value = errorData.message || 'System monitoring error'
      }
    })
  }

  const disconnect = () => {
    if (ws) {
      wsService.disconnect(null, 'system')
      connected.value = false
    }
  }

  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    connected,
    systemHealth,
    error,
    connect,
    disconnect
  }
}
```

### Vue Component Usage

```vue
<!-- Portfolio execution page -->
<template>
  <div class="portfolio-execution">
    <div class="connection-status" :class="{ connected, error: !!error }">
      <span v-if="connected" class="text-green-500">● Connected</span>
      <span v-else class="text-red-500">● Disconnected</span>
    </div>

    <div v-if="executionStatus === 'running'" class="execution-progress">
      <div class="progress-bar">
        <div 
          class="progress-fill" 
          :style="{ width: `${progress * 100}%` }"
        ></div>
      </div>
      <p class="activity-text">{{ currentActivity }}</p>
    </div>

    <div v-if="recommendations.length > 0" class="recommendations">
      <h3>Live Recommendations</h3>
      <div v-for="rec in recommendations" :key="rec.ticker" class="recommendation">
        <span class="ticker">{{ rec.ticker }}</span>
        <span class="action" :class="rec.action.toLowerCase()">{{ rec.action }}</span>
        <span class="confidence">{{ Math.round(rec.confidence * 100) }}%</span>
      </div>
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script setup>
import { usePortfolioWebSocket } from '@/composables/useWebSocket'

const props = defineProps({
  portfolioName: {
    type: String,
    required: true
  }
})

const {
  connected,
  executionStatus,
  progress,
  currentActivity,
  recommendations,
  error
} = usePortfolioWebSocket(props.portfolioName)
</script>
```

## Error Handling and Recovery

### Connection Error Types

1. **Network Errors**: Temporary network issues
2. **Server Errors**: Backend service unavailable
3. **Authentication Errors**: Invalid credentials (future feature)
4. **Rate Limiting**: Too many connections
5. **Protocol Errors**: Invalid message format

### Recovery Strategies

1. **Exponential Backoff**: Increasing delay between reconnect attempts
2. **Circuit Breaker**: Stop attempting after max failures
3. **Graceful Degradation**: Fall back to HTTP polling
4. **User Notification**: Inform user of connection status
5. **Automatic Retry**: Transparent reconnection when possible

## Testing WebSocket Connections

### Unit Testing

```python
# tests/test_websocket.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app

def test_portfolio_websocket_connection():
    client = TestClient(app)
    
    with client.websocket_connect("/api/agents/test-portfolio/ws") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "connection_established"
        assert data["data"]["portfolio_name"] == "test-portfolio"

def test_websocket_message_handling():
    client = TestClient(app)
    
    with client.websocket_connect("/api/agents/test-portfolio/ws") as websocket:
        # Send ping
        websocket.send_text("ping")
        
        # Should receive pong
        response = websocket.receive_json()
        assert response["type"] == "pong"
```

### Integration Testing

```javascript
// frontend/tests/websocket.test.js
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { wsService } from '@/services/websocket'

describe('WebSocket Service', () => {
  let mockWebSocket

  beforeEach(() => {
    mockWebSocket = {
      readyState: WebSocket.OPEN,
      send: vi.fn(),
      close: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn()
    }
    
    global.WebSocket = vi.fn(() => mockWebSocket)
  })

  afterEach(() => {
    wsService.disconnectAll()
  })

  it('should connect to portfolio WebSocket', () => {
    const callbacks = {
      onOpen: vi.fn(),
      onMessage: vi.fn()
    }
    
    wsService.connectPortfolio('test-portfolio', callbacks)
    
    expect(global.WebSocket).toHaveBeenCalledWith(
      'ws://localhost:8000/api/agents/test-portfolio/ws'
    )
  })

  it('should handle reconnection on connection loss', async () => {
    const callbacks = {
      onOpen: vi.fn(),
      onClose: vi.fn()
    }
    
    const ws = wsService.connectPortfolio('test-portfolio', callbacks)
    
    // Simulate connection loss
    mockWebSocket.onclose({ code: 1006 }) // Abnormal closure
    
    // Should attempt reconnection
    expect(callbacks.onClose).toHaveBeenCalled()
  })
})
```

## Performance Optimization

### Connection Management

1. **Connection Pooling**: Reuse connections when possible
2. **Message Batching**: Combine multiple updates into single messages
3. **Selective Updates**: Only send relevant data to each client
4. **Connection Limits**: Prevent resource exhaustion
5. **Memory Management**: Clean up dead connections promptly

### Message Optimization

1. **Compression**: Use WebSocket compression extensions
2. **Delta Updates**: Send only changed data
3. **Message Queuing**: Buffer messages during reconnection
4. **Priority Queuing**: Prioritize critical updates
5. **Rate Limiting**: Prevent message flooding

## Security Considerations

### Connection Security

1. **WSS Protocol**: Use secure WebSocket (WSS) in production
2. **Origin Validation**: Verify WebSocket origin headers
3. **Authentication**: Implement JWT-based WebSocket auth (future)
4. **Rate Limiting**: Prevent abuse and DoS attacks
5. **Message Validation**: Sanitize all incoming messages

### Data Protection

1. **Sensitive Data**: Avoid sending sensitive data over WebSocket
2. **Message Encryption**: Encrypt sensitive messages
3. **Access Control**: Verify client permissions for each message
4. **Audit Logging**: Log important WebSocket events
5. **Error Handling**: Don't leak system information in error messages

This comprehensive WebSocket integration guide provides everything needed to implement real-time features in FinTradeAgent, ensuring a responsive and reliable user experience.