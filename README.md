# 🌊 Flood Risk Predictor

A serverless, AI-powered application built on AWS that provides real-time flood risk analysis and sends targeted alerts to subscribed users.

## Inspiration
Flooding is one of the most common and costly natural disasters, affecting communities worldwide. The goal of this project was to create an accessible, proactive tool that could help individuals assess their risk in real-time and receive timely warnings, potentially saving property and lives. This solution leverages the power of serverless computing and generative AI to deliver a scalable and intelligent system.

---

## 🎥 Demo Video

[**Link to Your 3-Minute Demo Video Here**]

---

## 🌐 Live Demo

You can access the live application here:
**[Link to Your S3 Website URL Here]**

---

## 👨‍⚖️ Note for Hackathon Judges

**Reasoning:** This application uses Amazon SES, which is currently in a "sandbox" environment for security purposes. In this mode, alerts can only be sent to manually verified email addresses. I have explained clearly in the working demo how the entire process works.

---

## 🏛️ Architecture

The application is built on a 100% serverless architecture on AWS to ensure scalability, reliability, and cost-effectiveness.

![Architecture Diagram](architecture/architecture_diagram.png)

---

## ✨ Key Features

* **On-Demand Analysis**: Users can enter any city to get an immediate flood risk assessment powered by a Generative AI model.
* **Subscription Alerts**: Users can subscribe to receive proactive email alerts for specific locations.
* **Targeted Notifications**: The backend uses Amazon SES to send beautifully formatted HTML emails *only* to users subscribed to a high-risk location.
* **Automated & Scheduled**: An EventBridge schedule triggers a daily risk assessment for all subscribed locations, ensuring timely alerts.
* **Unsubscribe**: A simple, one-click feature allows users to unsubscribe from all alerts.

---

## 🛠️ Technology Stack

* **AWS Lambda**: Core compute for all backend logic.
* **Amazon API Gateway**: Exposes the backend logic as a public REST API for the frontend.
* **Amazon S3**: Hosts the static frontend website.
* **Amazon DynamoDB**: NoSQL database for storing user subscriptions and analysis results.
* **Amazon SES**: Sends targeted, high-quality HTML email alerts.
* **Amazon EventBridge Scheduler**: Triggers the scheduled risk analysis function.
* **Frontend**: HTML, CSS, vanilla JavaScript.
* **AI Model**: Gemini API for natural language-based risk assessment.
* **External APIs**: OpenWeatherMap and NewsAPI for real-time data ingestion.

---

## ⚙️ Configuration

The application is configured via environment variables in the Lambda functions, which include:

* API keys for external services (Gemini, OpenWeatherMap, NewsAPI).
* DynamoDB table names.
* The verified "From" email address for SES.