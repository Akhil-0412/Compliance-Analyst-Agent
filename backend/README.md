---
title: Agentic Compliance Analyst API
emoji: ⚖️
colorFrom: red
colorTo: pink
sdk: docker
pinned: false
license: mit
---

# Agentic Compliance Analyst - Backend API

A FastAPI backend for GDPR/CCPA compliance analysis powered by LLMs.

## Endpoints

- `GET /` - Health check
- `POST /api/chat` - Compliance query

## Environment Variables (Secrets)

Set these in your Space settings:
- `GROQ_API_KEY`
- `TAVILY_API_KEY`