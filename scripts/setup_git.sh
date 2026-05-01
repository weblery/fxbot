#!/bin/bash
echo "📦 Initializing Git Repository..."
git init
git checkout -b main

echo "📝 Staging core files (excluding data)..."
git add .
git commit -m "Initial commit: Professional Multi-Symbol Volatility Bot (v1.0)"

echo "🌿 Creating develop branch..."
git checkout -b develop

echo "✅ Git branches established: main (Stable) and develop (Ongoing Work)"
git branch
