/**
 * Demonstration Data for Flight Operations Module
 * 
 * Used during local development and preview mode.
 * Contains realistic operational telemetry, risk assessments,
 * multi-agent workflow statuses, and downstream dependencies.
 */

export const DEMO_OPERATIONAL_PULSE = {
  totalMonitoredFlights: 148,
  criticalRiskFlights: 4,
  highRiskFlights: 11,
  mediumRiskFlights: 22,
  nominalFlights: 111,
  onTimePercentage: 86.4,
  networkAverageDelayMinutes: 28,
  activeDisruptions: 5,
  proactiveSavingsEst: "$284,500",
  lastTelemetrySync: "2026-10-31T09:25:00Z",
  hubStatus: {
    JFK: { status: "GDP_ACTIVE", rate: "28/hr", delay: "+45m" },
    LHR: { status: "NORMAL", rate: "42/hr", delay: "Nominal" },
    ORD: { status: "WEATHER_WARN", rate: "34/hr", delay: "+25m" },
    FRA: { status: "CURFEW_CRITICAL", rate: "30/hr", delay: "+50m" }
  }
};

export const DEMO_FLIGHTS = [
  {
    id: "fl-1042",
    flightNumber: "AA-1042",
    airline: "American Airlines",
    origin: {
      code: "JFK",
      name: "New York John F. Kennedy",
      terminal: "T8",
      gate: "14B",
      scheduledTime: "14:30",
      estimatedTime: "16:15",
      runway: "31L"
    },
    destination: {
      code: "LHR",
      name: "London Heathrow",
      terminal: "T3",
      gate: "Gate 18",
      scheduledTime: "22:45",
      estimatedTime: "00:30",
      runway: "27R"
    },
    aircraft: {
      model: "Boeing 777-300ER",
      tailNumber: "N780AA",
      capacity: 304,
      passengerLoad: 286,
      cargoWeightKg: 14200
    },
    status: "Critical Risk",
    priority: "CRITICAL",
    delayMinutes: 105,
    delayReason: "Severe convective cell over departure corridor combined with imminent crew legal duty expiration.",
    riskScore: 88,
    riskLevel: "CRITICAL",
    riskFactors: [
      {
        category: "Crew Legality",
        severity: "CRITICAL",
        score: 94,
        weight: "35%",
        description: "Cockpit crew duty ceiling (14 hrs FAA limit) expires in 62 minutes. If departure is not achieved by 15:32 UTC, crew times out."
      },
      {
        category: "Weather & ATC Slot",
        severity: "HIGH",
        score: 86,
        weight: "25%",
        description: "EDCT ground stop active at JFK; severe microburst cell tracking 12 miles east of departure fix."
      },
      {
        category: "Downstream Curfew",
        severity: "HIGH",
        score: 84,
        weight: "20%",
        description: "Estimated LHR arrival of 00:30 UTC jeopardizes London Heathrow night flight quota restrictions (06:00 curfew penalty £22,000)."
      },
      {
        category: "Passenger Missed Connections",
        severity: "HIGH",
        score: 80,
        weight: "15%",
        description: "48 onward connecting passengers to European and Asian routes face sub-40-minute transfer times at Heathrow."
      },
      {
        category: "Maintenance & Turnaround",
        severity: "LOW",
        score: 22,
        weight: "5%",
        description: "Airframe mechanical log clean. Turnaround fueling slowed solely by ramp safety lightning pause."
      }
    ],
    dependencies: {
      inboundFlight: "AA-930 (MIA -> JFK, landed +32m delayed)",
      turnaroundMinutes: 80,
      turnaroundStatus: "Tight Buffer (8m remaining)",
      connectingPassengers: 64,
      connectingFlights: [
        { flight: "BA-1440 (LHR -> EDI)", passengers: 18, scheduledConnectWindow: "50m", status: "CRITICAL_RISK" },
        { flight: "BA-872 (LHR -> FRA)", passengers: 16, scheduledConnectWindow: "55m", status: "HIGH_RISK" },
        { flight: "BA-138 (LHR -> BOM)", passengers: 14, scheduledConnectWindow: "65m", status: "MEDIUM_RISK" }
      ],
      crewHandoff: "Reserve Crew Flight Deck Team Bravo stationed at JFK Terminal 8 (Ready in 20m)"
    },
    impactAnalysis: {
      missedConnections: 34,
      passengerCompensationEst: 42000,
      downstreamDelayMinutes: 90,
      curfewRisk: true,
      curfewAirport: "London Heathrow (LHR)",
      totalFinancialImpact: 64000
    },
    recommendation: {
      id: "rec-1042-01",
      action: "AIRCRAFT_SWAP_AND_CREW_REASSIGNMENT",
      title: "Immediate Standby Aircraft Swap & Reserve Crew Bravo Deployment",
      confidenceScore: 94,
      reasoning: "Swapping to standby Boeing 777-300ER (Gate 12, ready in 25m) and activating Reserve Crew Bravo clears departure within the JFK weather corridor gap, averts 34 missed European connections, and circumvents the £22,000 LHR night curfew fine.",
      estimatedSavings: "$44,000 & 85 mins delay reduction",
      alternativeActions: [
        "Maintain current airframe & crew: 89% probability crew will timeout at hold pad, inducing flight cancellation costing $115,000.",
        "Re-accommodate passengers onto BA-178: Only 14 seats available in Business/Economy; insufficient capacity."
      ],
      status: "PENDING_APPROVAL",
      approvedBy: null,
      reviewedBy: null,
      timestamp: "2026-10-31T09:22:15Z"
    },
    agentWorkflow: [
      {
        stage: "Telemetry & Weather Ingestion",
        agent: "AeroPulse Weather Watcher",
        status: "COMPLETED",
        timestamp: "09:12:04",
        detail: "Real-time radar detected cell development directly over JFK Departure Runway 31L."
      },
      {
        stage: "Crew Legality & Rule Solver",
        agent: "Crew Legal Compliance Engine",
        status: "COMPLETED",
        timestamp: "09:14:21",
        detail: "Flagged strict FAR 117 duty ceiling expiration within 62 minutes."
      },
      {
        stage: "Downstream Passenger Network Impact",
        agent: "Network Propagation Solver",
        status: "COMPLETED",
        timestamp: "09:16:48",
        detail: "Projected 34 missed European connections and €600 EU261 compensation exposure."
      },
      {
        stage: "Autonomous Mitigation Synthesizer",
        agent: "Fleet Optimization Agent",
        status: "COMPLETED",
        timestamp: "09:18:30",
        detail: "Synthesized 3 feasible options; selected Reserve Crew + Gate 12 Standby Swap."
      },
      {
        stage: "Operations Dispatcher Sign-Off",
        agent: "Human-in-the-Loop Dispatch Portal",
        status: "AWAITING_ACTION",
        timestamp: "09:20:00",
        detail: "Queued for immediate duty manager authorization."
      }
    ],
    historicalTrend: [
      { time: "T-120m", score: 22, delay: 0 },
      { time: "T-90m", score: 38, delay: 20 },
      { time: "T-60m", score: 62, delay: 55 },
      { time: "T-30m", score: 79, delay: 85 },
      { time: "Now", score: 88, delay: 105 }
    ]
  },
  {
    id: "fl-891",
    flightNumber: "UA-891",
    airline: "United Airlines",
    origin: {
      code: "ORD",
      name: "Chicago O'Hare",
      terminal: "T1",
      gate: "C19",
      scheduledTime: "15:10",
      estimatedTime: "16:25",
      runway: "10L"
    },
    destination: {
      code: "NRT",
      name: "Tokyo Narita",
      terminal: "T1",
      gate: "Gate 32",
      scheduledTime: "19:05",
      estimatedTime: "20:20",
      runway: "16R"
    },
    aircraft: {
      model: "Boeing 787-9 Dreamliner",
      tailNumber: "N29985",
      capacity: 257,
      passengerLoad: 248,
      cargoWeightKg: 18500
    },
    status: "Delayed",
    priority: "HIGH",
    delayMinutes: 75,
    delayReason: "Hydraulic sensor minor advisory on pre-flight inspection; replacement valve signed off by Line Tech.",
    riskScore: 74,
    riskLevel: "HIGH",
    riskFactors: [
      {
        category: "Maintenance",
        severity: "HIGH",
        score: 78,
        weight: "35%",
        description: "Hydraulic sensor advisory cleared under sign-off; waiting on final maintenance log sign."
      },
      {
        category: "ATC Slot / Flow",
        severity: "MEDIUM",
        score: 65,
        weight: "25%",
        description: "Midwest airspace departure metering slot assigned (+35m window)."
      },
      {
        category: "Crew Legality",
        severity: "MEDIUM",
        score: 58,
        weight: "20%",
        description: "Augmented 4-pilot trans-Pacific crew has 2h 45m buffer before FAA duty restriction."
      },
      {
        category: "Downstream Connections",
        severity: "MEDIUM",
        score: 62,
        weight: "20%",
        description: "22 passengers onward to Bangkok and Singapore with 1h 15m transfer window."
      }
    ],
    dependencies: {
      inboundFlight: "UA-402 (SFO -> ORD, landed on schedule)",
      turnaroundMinutes: 95,
      turnaroundStatus: "Extended for maintenance check",
      connectingPassengers: 42,
      connectingFlights: [
        { flight: "NH-805 (NRT -> BKK)", passengers: 14, scheduledConnectWindow: "75m", status: "MEDIUM_RISK" },
        { flight: "SQ-637 (NRT -> SIN)", passengers: 8, scheduledConnectWindow: "60m", status: "HIGH_RISK" }
      ],
      crewHandoff: "Flight deck signed on duty; cabin crew assembled"
    },
    impactAnalysis: {
      missedConnections: 8,
      passengerCompensationEst: 9600,
      downstreamDelayMinutes: 50,
      curfewRisk: false,
      curfewAirport: "None",
      totalFinancialImpact: 14800
    },
    recommendation: {
      id: "rec-891-01",
      action: "FAST_TRACK_RAMP_BOARDING",
      title: "Expedited Boarding Parallel to Final Line Sign-off",
      confidenceScore: 91,
      reasoning: "Simultaneously running dual-jetway boarding while maintenance supervisor enters digital clearance in ACARS will recover 25 minutes and safeguard all Tokyo connections.",
      estimatedSavings: "$11,200 & 25 mins delay recovery",
      alternativeActions: [
        "Sequential boarding post-maintenance: Additional 25m delay guarantees missing Singapore connections."
      ],
      status: "PENDING_APPROVAL",
      approvedBy: null,
      reviewedBy: null,
      timestamp: "2026-10-31T09:21:00Z"
    },
    agentWorkflow: [
      {
        stage: "Maintenance Telemetry Hook",
        agent: "TechOps Sensor Monitor",
        status: "COMPLETED",
        timestamp: "09:08:10",
        detail: "Sensor fault cleared; hydraulic pressure test passed nominal at 3,000 psi."
      },
      {
        stage: "Ramp Turnaround Tracker",
        agent: "Ground Operations Agent",
        status: "COMPLETED",
        timestamp: "09:12:40",
        detail: "Baggage 100% loaded; catering complete; refueling sealed."
      },
      {
        stage: "Network Transfer Analysis",
        agent: "Passenger Value Optimization Agent",
        status: "COMPLETED",
        timestamp: "09:15:18",
        detail: "Calculated 91% connection probability if wheels up within 35 minutes."
      },
      {
        stage: "Operations Dispatcher Sign-Off",
        agent: "Human-in-the-Loop Dispatch Portal",
        status: "AWAITING_ACTION",
        timestamp: "09:17:00",
        detail: "Awaiting dispatcher approval for dual-jetway parallel boarding."
      }
    ],
    historicalTrend: [
      { time: "T-120m", score: 18, delay: 0 },
      { time: "T-90m", score: 45, delay: 30 },
      { time: "T-60m", score: 72, delay: 60 },
      { time: "T-30m", score: 76, delay: 75 },
      { time: "Now", score: 74, delay: 75 }
    ]
  },
  {
    id: "fl-430",
    flightNumber: "LH-430",
    airline: "Lufthansa",
    origin: {
      code: "ORD",
      name: "Chicago O'Hare",
      terminal: "T5",
      gate: "M12",
      scheduledTime: "16:00",
      estimatedTime: "17:35",
      runway: "28R"
    },
    destination: {
      code: "FRA",
      name: "Frankfurt Main",
      terminal: "T1",
      gate: "B44",
      scheduledTime: "07:30",
      estimatedTime: "09:05",
      runway: "07L"
    },
    aircraft: {
      model: "Airbus A350-900",
      tailNumber: "D-AIXN",
      capacity: 293,
      passengerLoad: 281,
      cargoWeightKg: 12800
    },
    status: "Critical Risk",
    priority: "CRITICAL",
    delayMinutes: 95,
    delayReason: "Inbound aircraft delay + Frankfurt strict night curfew window risk.",
    riskScore: 84,
    riskLevel: "CRITICAL",
    riskFactors: [
      {
        category: "Downstream Curfew",
        severity: "CRITICAL",
        score: 91,
        weight: "40%",
        description: "Frankfurt airport strict night flight ban starts at 23:00 local; delay cascades into return turnaround bank."
      },
      {
        category: "Weather",
        severity: "MEDIUM",
        score: 55,
        weight: "20%",
        description: "North Atlantic track headwinds currently 65 knots higher than standard seasonal average."
      },
      {
        category: "Passenger Missed Connections",
        severity: "HIGH",
        score: 82,
        weight: "25%",
        description: "72 passengers connecting to Lufthansa Schengen bank at Frankfurt (35m transfer minimum)."
      },
      {
        category: "Crew Legality",
        severity: "LOW",
        score: 30,
        weight: "15%",
        description: "Fresh rest crew reporting from Chicago layover hotel."
      }
    ],
    dependencies: {
      inboundFlight: "LH-431 (FRA -> ORD, arrived +70m delayed)",
      turnaroundMinutes: 65,
      turnaroundStatus: "Compressed turnaround underway",
      connectingPassengers: 72,
      connectingFlights: [
        { flight: "LH-1110 (FRA -> MAD)", passengers: 22, scheduledConnectWindow: "45m", status: "CRITICAL_RISK" },
        { flight: "LH-1234 (FRA -> VIE)", passengers: 19, scheduledConnectWindow: "50m", status: "HIGH_RISK" }
      ],
      crewHandoff: "Operating crew checked in on dispatch pad"
    },
    impactAnalysis: {
      missedConnections: 41,
      passengerCompensationEst: 51000,
      downstreamDelayMinutes: 80,
      curfewRisk: true,
      curfewAirport: "Frankfurt (FRA)",
      totalFinancialImpact: 78500
    },
    recommendation: {
      id: "rec-430-01",
      action: "OPTIMIZE_NORTH_ATLANTIC_ROUTING",
      title: "Request High-Speed NAT Track Zulu & Priority Push",
      confidenceScore: 92,
      reasoning: "Filing high-speed Oceanic track Mach 0.85 (burns +1,400 kg fuel) cuts 28 minutes flight time, securing Frankfurt arrival at 08:37 local and saving 41 Schengen flight transfers.",
      estimatedSavings: "$38,000 & 28 mins airborne recovery",
      alternativeActions: [
        "Standard Mach 0.82 profile: Saves $2,800 fuel but incurs $51,000 in hotel vouchers and missed flight re-bookings."
      ],
      status: "PENDING_APPROVAL",
      approvedBy: null,
      reviewedBy: null,
      timestamp: "2026-10-31T09:22:00Z"
    },
    agentWorkflow: [
      {
        stage: "Oceanic Flight Plan Optimization",
        agent: "Flight Planning Agent",
        status: "COMPLETED",
        timestamp: "09:14:10",
        detail: "Simulated 5 NAT tracks with Eurocontrol & Gander Oceanic controllers."
      },
      {
        stage: "Fuel & Cost Benefit Evaluation",
        agent: "AeroEconomics Optimizer",
        status: "COMPLETED",
        timestamp: "09:16:30",
        detail: "Net operational gain of $35,200 factoring additional Jet-A burn."
      },
      {
        stage: "Operations Dispatcher Sign-Off",
        agent: "Human-in-the-Loop Dispatch Portal",
        status: "AWAITING_ACTION",
        timestamp: "09:19:00",
        detail: "Awaiting flight dispatcher ACARS dispatch uplink authorization."
      }
    ],
    historicalTrend: [
      { time: "T-120m", score: 30, delay: 10 },
      { time: "T-90m", score: 50, delay: 40 },
      { time: "T-60m", score: 70, delay: 70 },
      { time: "T-30m", score: 81, delay: 85 },
      { time: "Now", score: 84, delay: 95 }
    ]
  },
  {
    id: "fl-482",
    flightNumber: "DL-482",
    airline: "Delta Air Lines",
    origin: {
      code: "ATL",
      name: "Atlanta Hartsfield-Jackson",
      terminal: "T-South",
      gate: "B12",
      scheduledTime: "15:45",
      estimatedTime: "16:20",
      runway: "09L"
    },
    destination: {
      code: "LAX",
      name: "Los Angeles Intl",
      terminal: "T2",
      gate: "Gate 24",
      scheduledTime: "18:00",
      estimatedTime: "18:35",
      runway: "25L"
    },
    aircraft: {
      model: "Airbus A321neo",
      tailNumber: "N501DA",
      capacity: 194,
      passengerLoad: 188,
      cargoWeightKg: 4200
    },
    status: "Delayed",
    priority: "MEDIUM",
    delayMinutes: 35,
    delayReason: "Baggage transfer conveyor belt stoppage at Terminal South; baggage handlers manually sorting.",
    riskScore: 48,
    riskLevel: "MEDIUM",
    riskFactors: [
      {
        category: "Ramp / Baggage",
        severity: "MEDIUM",
        score: 60,
        weight: "35%",
        description: "Conveyor system rebooted; ramp crews loading remaining 28 transfer containers."
      },
      {
        category: "ATC Flow",
        severity: "LOW",
        score: 35,
        weight: "25%",
        description: "Atlanta airspace traffic density normal; no ground hold active."
      },
      {
        category: "Downstream Aircraft Utilization",
        severity: "MEDIUM",
        score: 52,
        weight: "25%",
        description: "Aircraft turns to LAX-HNL with 1h 40m scheduled turnaround buffer."
      },
      {
        category: "Crew Legality",
        severity: "LOW",
        score: 20,
        weight: "15%",
        description: "Crew within duty hours limits."
      }
    ],
    dependencies: {
      inboundFlight: "DL-1102 (MCO -> ATL, arrived on time)",
      turnaroundMinutes: 55,
      turnaroundStatus: "Baggage delay (+25m)",
      connectingPassengers: 18,
      connectingFlights: [
        { flight: "DL-834 (LAX -> HNL)", passengers: 12, scheduledConnectWindow: "95m", status: "LOW_RISK" }
      ],
      crewHandoff: "Operating crew onboard"
    },
    impactAnalysis: {
      missedConnections: 2,
      passengerCompensationEst: 1800,
      downstreamDelayMinutes: 20,
      curfewRisk: false,
      curfewAirport: "None",
      totalFinancialImpact: 4200
    },
    recommendation: {
      id: "rec-482-01",
      action: "CLOSE_CARGO_DOOR_DISPATCH_EXPEDITE",
      title: "Authorize Final Container Lock & Priority Pushback",
      confidenceScore: 89,
      reasoning: "Last baggage cart confirmed at 16:12; prompt door closure allows taxi slot before peak departure bank at 16:30.",
      estimatedSavings: "$3,500 & 15 mins turnaround recovery",
      alternativeActions: [
        "Wait for standby baggage reconciliation: Adds 20 mins delay without additional passenger bags."
      ],
      status: "PENDING_APPROVAL",
      approvedBy: null,
      reviewedBy: null,
      timestamp: "2026-10-31T09:23:00Z"
    },
    agentWorkflow: [
      {
        stage: "Baggage Telemetry Sync",
        agent: "Luggage Tracker Agent",
        status: "COMPLETED",
        timestamp: "09:16:00",
        detail: "182/188 scanned bags in hold; final 6 scanned at ramp."
      },
      {
        stage: "Ground Operations Agent",
        agent: "Ramp Turnaround Tracker",
        status: "COMPLETED",
        timestamp: "09:19:12",
        detail: "Towbar connected and pushback tug in position."
      },
      {
        stage: "Operations Dispatcher Sign-Off",
        agent: "Human-in-the-Loop Dispatch Portal",
        status: "AWAITING_ACTION",
        timestamp: "09:21:00",
        detail: "Awaiting ramp controller dispatch confirmation."
      }
    ],
    historicalTrend: [
      { time: "T-120m", score: 10, delay: 0 },
      { time: "T-90m", score: 18, delay: 5 },
      { time: "T-60m", score: 38, delay: 20 },
      { time: "T-30m", score: 45, delay: 35 },
      { time: "Now", score: 48, delay: 35 }
    ]
  },
  {
    id: "fl-178",
    flightNumber: "BA-178",
    airline: "British Airways",
    origin: {
      code: "JFK",
      name: "New York John F. Kennedy",
      terminal: "T8",
      gate: "16",
      scheduledTime: "17:15",
      estimatedTime: "17:25",
      runway: "31L"
    },
    destination: {
      code: "LHR",
      name: "London Heathrow",
      terminal: "T5",
      gate: "C52",
      scheduledTime: "05:15",
      estimatedTime: "05:25",
      runway: "27L"
    },
    aircraft: {
      model: "Boeing 777-200ER",
      tailNumber: "G-VIIA",
      capacity: 272,
      passengerLoad: 260,
      cargoWeightKg: 11200
    },
    status: "Boarding",
    priority: "LOW",
    delayMinutes: 10,
    delayReason: "Minor departure queue metering; flight operates within nominal buffer.",
    riskScore: 24,
    riskLevel: "LOW",
    riskFactors: [
      {
        category: "ATC Flow",
        severity: "LOW",
        score: 28,
        weight: "40%",
        description: "Standard JFK evening metering; slot locked."
      },
      {
        category: "Weather",
        severity: "LOW",
        score: 22,
        weight: "30%",
        description: "Departure path cleared of convective clouds."
      },
      {
        category: "Crew Legality",
        severity: "LOW",
        score: 15,
        weight: "30%",
        description: "Crew well within legal limits."
      }
    ],
    dependencies: {
      inboundFlight: "BA-179 (LHR -> JFK, arrived on time)",
      turnaroundMinutes: 90,
      turnaroundStatus: "Turnaround complete ahead of schedule",
      connectingPassengers: 55,
      connectingFlights: [
        { flight: "BA-762 (LHR -> OSL)", passengers: 15, scheduledConnectWindow: "90m", status: "LOW_RISK" }
      ],
      crewHandoff: "Operating crew aboard"
    },
    impactAnalysis: {
      missedConnections: 0,
      passengerCompensationEst: 0,
      downstreamDelayMinutes: 5,
      curfewRisk: false,
      curfewAirport: "None",
      totalFinancialImpact: 0
    },
    recommendation: {
      id: "rec-178-01",
      action: "MONITOR_ONLY",
      title: "Maintain Standard Operating Protocol",
      confidenceScore: 98,
      reasoning: "Flight operations nominal; tailwind on oceanic sector will absorb 10m departure metering.",
      estimatedSavings: "No mitigation required",
      alternativeActions: [],
      status: "PENDING_APPROVAL",
      approvedBy: null,
      reviewedBy: null,
      timestamp: "2026-10-31T09:20:00Z"
    },
    agentWorkflow: [
      {
        stage: "Nominal Flight Tracking",
        agent: "AeroPulse Global Sentinel",
        status: "COMPLETED",
        timestamp: "09:20:00",
        detail: "All flight indicators green."
      }
    ],
    historicalTrend: [
      { time: "T-120m", score: 15, delay: 0 },
      { time: "T-90m", score: 20, delay: 0 },
      { time: "T-60m", score: 22, delay: 5 },
      { time: "T-30m", score: 25, delay: 10 },
      { time: "Now", score: 24, delay: 10 }
    ]
  },
  {
    id: "fl-201",
    flightNumber: "EK-201",
    airline: "Emirates",
    origin: {
      code: "DXB",
      name: "Dubai International",
      terminal: "T3",
      gate: "A01",
      scheduledTime: "18:30",
      estimatedTime: "18:30",
      runway: "12R"
    },
    destination: {
      code: "JFK",
      name: "New York John F. Kennedy",
      terminal: "T4",
      gate: "B20",
      scheduledTime: "04:15",
      estimatedTime: "04:15",
      runway: "22L"
    },
    aircraft: {
      model: "Airbus A380-800",
      tailNumber: "A6-EEO",
      capacity: 516,
      passengerLoad: 498,
      cargoWeightKg: 22000
    },
    status: "On Time",
    priority: "LOW",
    delayMinutes: 0,
    delayReason: "Operating strictly on schedule. Zero operational anomalies.",
    riskScore: 12,
    riskLevel: "LOW",
    riskFactors: [
      {
        category: "Weather",
        severity: "LOW",
        score: 10,
        weight: "40%",
        description: "Clear skies across UAE and polar routing."
      },
      {
        category: "Airframe",
        severity: "LOW",
        score: 12,
        weight: "30%",
        description: "A380 systems checked and certified 100% nominal."
      },
      {
        category: "Crew Legality",
        severity: "LOW",
        score: 14,
        weight: "30%",
        description: "4-pilot crew rested with complete reserve support."
      }
    ],
    dependencies: {
      inboundFlight: "EK-405 (MEL -> DXB, arrived on time)",
      turnaroundMinutes: 120,
      turnaroundStatus: "Completed on time",
      connectingPassengers: 140,
      connectingFlights: [],
      crewHandoff: "Operating crew aboard"
    },
    impactAnalysis: {
      missedConnections: 0,
      passengerCompensationEst: 0,
      downstreamDelayMinutes: 0,
      curfewRisk: false,
      curfewAirport: "None",
      totalFinancialImpact: 0
    },
    recommendation: {
      id: "rec-201-01",
      action: "STANDARD_DISPATCH",
      title: "Proceed with Standard Departure Clearance",
      confidenceScore: 99,
      reasoning: "Flight parameters in optimal state.",
      estimatedSavings: "Nominal operation",
      alternativeActions: [],
      status: "APPROVED",
      approvedBy: "System Dispatcher Auto-Pass",
      reviewedBy: "Chief Operations Officer",
      timestamp: "2026-10-31T09:10:00Z"
    },
    agentWorkflow: [
      {
        stage: "Autonomous Dispatch Check",
        agent: "AeroPulse Global Sentinel",
        status: "COMPLETED",
        timestamp: "09:05:00",
        detail: "Dispatched without manual intervention."
      }
    ],
    historicalTrend: [
      { time: "T-120m", score: 12, delay: 0 },
      { time: "T-90m", score: 12, delay: 0 },
      { time: "T-60m", score: 12, delay: 0 },
      { time: "T-30m", score: 12, delay: 0 },
      { time: "Now", score: 12, delay: 0 }
    ]
  },
  {
    id: "fl-006",
    flightNumber: "AF-006",
    airline: "Air France",
    origin: {
      code: "CDG",
      name: "Paris Charles de Gaulle",
      terminal: "2E",
      gate: "K35",
      scheduledTime: "13:40",
      estimatedTime: "13:55",
      runway: "08L"
    },
    destination: {
      code: "JFK",
      name: "New York John F. Kennedy",
      terminal: "T1",
      gate: "Gate 4",
      scheduledTime: "16:20",
      estimatedTime: "16:35",
      runway: "04R"
    },
    aircraft: {
      model: "Boeing 777-300ER",
      tailNumber: "F-GSQC",
      capacity: 296,
      passengerLoad: 282,
      cargoWeightKg: 15400
    },
    status: "In Flight",
    priority: "LOW",
    delayMinutes: 15,
    delayReason: "En-route speed adjustment to match JFK arrival slot timing.",
    riskScore: 28,
    riskLevel: "LOW",
    riskFactors: [
      {
        category: "Air Traffic Metering",
        severity: "LOW",
        score: 30,
        weight: "50%",
        description: "En route over Nova Scotia; holding pattern avoided."
      },
      {
        category: "Fuel Reserve",
        severity: "LOW",
        score: 18,
        weight: "50%",
        description: "3,800 kg reserve fuel above international contingency requirements."
      }
    ],
    dependencies: {
      inboundFlight: "AF-007 (JFK -> CDG, previous cycle)",
      turnaroundMinutes: 80,
      turnaroundStatus: "En route",
      connectingPassengers: 35,
      connectingFlights: [
        { flight: "DL-2190 (JFK -> MCO)", passengers: 12, scheduledConnectWindow: "1h 45m", status: "LOW_RISK" }
      ],
      crewHandoff: "Operating in-flight crew"
    },
    impactAnalysis: {
      missedConnections: 0,
      passengerCompensationEst: 0,
      downstreamDelayMinutes: 5,
      curfewRisk: false,
      curfewAirport: "None",
      totalFinancialImpact: 0
    },
    recommendation: {
      id: "rec-006-01",
      action: "CRUISE_ALTITUDE_OPTIMIZATION",
      title: "Step Climb to FL380 at Waypoint ENE",
      confidenceScore: 96,
      reasoning: "Step climb takes advantage of 25kt tailwind decrease and saves 420 kg fuel on descent.",
      estimatedSavings: "$650 fuel reduction",
      alternativeActions: [],
      status: "APPROVED",
      approvedBy: "En-Route Flight Dispatcher 118",
      reviewedBy: null,
      timestamp: "2026-10-31T09:12:00Z"
    },
    agentWorkflow: [
      {
        stage: "En-Route Oceanic Radar Sync",
        agent: "Flight Sentinel Oceanic Agent",
        status: "COMPLETED",
        timestamp: "09:11:00",
        detail: "ACARS altitude request communicated to Boston ARTCC."
      }
    ],
    historicalTrend: [
      { time: "T-120m", score: 20, delay: 0 },
      { time: "T-90m", score: 25, delay: 10 },
      { time: "T-60m", score: 28, delay: 15 },
      { time: "T-30m", score: 28, delay: 15 },
      { time: "Now", score: 28, delay: 15 }
    ]
  }
];
