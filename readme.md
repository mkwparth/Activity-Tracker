# Human Activity Data Engineering Project

## Overview

This project is a data engineering pipeline designed to capture and analyze human interaction with a computer system.

The application records user activity such as:

- Mouse movements  
- Mouse clicks  
- Mouse scroll events  
- Keyboard key presses  
- Active window information  
- Timestamps for all events  

The captured data is stored in structured JSON files and will later be processed to generate insights about application usage, activity patterns, and engagement metrics.

The long-term goal of this project is to transform raw interaction data into meaningful analytics and dashboards that show:

- Time spent per application  
- User activity levels  
- Interaction intensity  
- Behavioral trends  

---

## Project Architecture (High Level)

1. **Extractor (Python Application)**  
   Captures real-time mouse and keyboard interactions along with active window details.

2. **Storage Layer**  
   Raw interaction data is stored in JSON format. Files are intended to be uploaded to cloud storage (e.g., S3).

3. **Transformation Layer (dbt)**  
   Raw data will be transformed into structured models for analytics.

4. **Analytics & Dashboard Layer**  
   Aggregated insights will be visualized through dashboards.

---

## Technologies Used

### Programming & Extraction
- Python  
- `pynput` (Keyboard and mouse event capture)  
- `pygetwindow` (Active window detection)  
- `dataclasses` (Structured event modeling)  
- JSON (Raw data storage)  

### Data Engineering & Processing
- Amazon S3 (Cloud storage for raw files)  
- dbt (Data transformation)  
- SQL-based analytics  

### Future Visualization
- BI / Dashboard tools (to be defined)  

---

## Current Status

The project currently includes:

- A lightweight Python-based activity extractor  
- Real-time event capture  
- JSON file generation  
- Thread-safe event logging  
- Configurable mouse event throttling  

Additional features such as hourly file rotation, S3 upload automation, and transformation models will be added in future iterations.

---

## Goal

To build a complete end-to-end data engineering pipeline that transforms raw human-computer interaction data into actionable behavioral insights.

---

This README provides a high-level description. Technical implementation details and architecture documentation will be added as the project evolves.
