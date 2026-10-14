# EDITH: Disaster-Response Healthcare Coordination Platform

> **Emergency Delivery & Inter-Facility Transfer Hub**  
> An offline-aware, human-directed emergency healthcare coordination platform designed for disaster environments (floods, cyclones, intermittent connectivity).

---

## 📌 Project Overview

During natural disasters, healthcare infrastructure faces acute supply shortages alongside severed or degraded communication channels. The primary bottleneck is an acute failure of coordination: fragmented phone calls, unmonitored chat groups, unacknowledged requests, and ambiguous responsibility.

**EDITH** solves this by connecting authorized hospitals, medical relief camps, and an Incident Command Centre (ICC) to manage emergency resource requests, voluntary offers, approved assignments, transit progress, and receipt-verified delivery.

### Core Principles
- **Request-Centric**: Facilities broadcast urgent needs; peers offer what they can spare.
- **Human-Controlled**: Incident Command Centre validates offers, authorizes transfers, and verifies resolution.
- **Offline-Aware**: Disconnected devices can draft requests, log deliveries, and queue sync operations in local storage (IndexedDB) with visual draft/synced indicators.
- **Accountable & Auditable**: Cryptographic receipt verification and tamper-evident audit trails.

---

## 📁 Repository Structure

```
EDITH/
├── documents/
│   ├── PRD.md                       # Product Requirements Document
│   ├── SYSTEM_ARCHITECTURE.md       # Technical Architecture & Data Models
│   ├── IMPLEMENTATION.md            # Implementation Plan & Technical Specifications
│   ├── DEVELOPMENT_PHASES.md        # Staged Development Roadmap
│   └── EDITH_System_design.pdf      # Architectural Blueprint Diagrams
├── presentation/
│   ├── EDITH_Hackathon_Pitch_Deck.pdf # Pitch Deck PDF
│   ├── EDITH_Hackathon_Pitch_Deck.pptx# Pitch Deck PowerPoint
│   ├── presentation.html            # Web-based Interactive Presentation Deck
│   └── ...scripts for deck building and asset generation
└── EDITH_Presentation_Assets/       # Exported slide deck high-resolution visuals
```

---

## 🚀 Key Features

- **Offline-First PWA Architecture**: Reliable operation during network dropouts and low-bandwidth scenarios.
- **Role-Based Incident Command**: Dedicated consoles for Requesting Facilities, Donating Facilities, Couriers, and ICC Admins.
- **Handover Verification**: OTP and digital verification protocols for secure custody transfers.
- **Audit Trails**: Complete lifecycle logging for full post-incident transparency.
