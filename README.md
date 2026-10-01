# AI Automated Code Review System

An AI-powered security code review platform that analyzes GitHub Pull Requests and automatically detects potential security vulnerabilities using a combination of **deterministic security rules** and **AI-based analysis**.

## Overview

The AI Automated Code Review System allows developers to submit a GitHub Pull Request URL and receive an automated security review of the code changes.

The system:

- Fetches the Pull Request diff directly from GitHub.
- Analyzes changed code using deterministic security rules.
- Uses Google's Gemini API for AI-based security analysis.
- Detects multiple vulnerabilities in a single Pull Request.
- Aggregates and deduplicates findings from different review agents.
- Returns structured security findings through a REST API.
- Supports quick PR reviews without requiring user authentication.

## Features

- GitHub Pull Request URL-based review
- Automatic Pull Request diff retrieval
- Deterministic security vulnerability detection
- AI-powered security analysis
- Multiple vulnerability detection
- Finding aggregation and deduplication
- Severity classification
- Confidence scoring
- GitHub API integration
- REST API using Django REST Framework
- Structured JSON responses
- No authentication required for basic PR review

## Vulnerabilities Detected

The current review engine can identify vulnerabilities such as:

- **Arbitrary code execution** through `eval()`
- **SQL injection**
- **Hardcoded API keys and secrets**
- **Password and sensitive-data logging**
- Other security weaknesses identified by the AI reviewer

## Architecture

```text
                         User
                           |
                           v
                    GitHub PR URL
                           |
                           v
                  Django REST API
                           |
                           v
                    Validate URL
                           |
                           v
                    GitHub API
                           |
                           v
                       PR Diff
                           |
              +------------+------------+
              |                         |
              v                         v
       Baseline Reviewer          AI Reviewer
              |                         |
              |                         |
              +------------+------------+
                           |
                           v
                     Aggregator
                           |
                     Deduplication
                           |
                           v
                  Final Findings
                           |
                           v
                    JSON Response