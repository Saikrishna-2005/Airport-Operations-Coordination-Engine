import api from "../api";
import { DEMO_FLIGHTS, DEMO_OPERATIONAL_PULSE } from '../data/demoFlights';

/**
 * Axios API Service Layer for Flight Operations
 * 
 * Configured to communicate with FastAPI backend endpoints.
 * Includes seamless fallback to local demonstration data when backend
 * is offline or when running in standalone demo mode.
 */

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
export const USE_DEMO_DATA = import.meta.env.VITE_USE_DEMO_DATA !== 'false';

// Create configured Axios instance
export const apiClient = api;

// In-memory demo state store to support dynamic updates (approvals, simulations) during demo sessions
let localFlightsState = JSON.parse(JSON.stringify(DEMO_FLIGHTS));

// Helper for simulated network delay in demo mode (enhances realistic UX testing)
const demoDelay = (ms = 250) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Fetch all flights for the priority board and search index
 * Endpoint: GET /flights
 */
export const getAllFlights = async () => {
  try {
    // apiClient already points to http://127.0.0.1:8000 and attaches the JWT.
    const response = await apiClient.get('/api/flights/');
    if (!Array.isArray(response.data)) {
      throw new Error('Invalid flight list received from backend');
    }

    const flights = response.data.map((flight) => {
      const riskScore = Number(flight.risk_score ?? 0);
      const riskLevel = riskScore >= 75 ? 'CRITICAL'
        : riskScore >= 50 ? 'HIGH'
        : riskScore >= 25 ? 'MEDIUM' : 'LOW';

      return {
        ...flight,
        id: flight.id,
        flightNumber: flight.flight_number,
        airline: flight.airline,
        origin: {
          code: flight.origin_code,
          name: flight.origin_name ?? flight.origin_code,
        },
        destination: {
          code: flight.destination_code,
          name: flight.destination_name ?? flight.destination_code,
        },
        aircraftRegistration: flight.aircraft_registration,
        aircraftType: flight.aircraft_type,
        scheduledDeparture: flight.scheduled_departure,
        estimatedDeparture: flight.estimated_departure,
        actualDeparture: flight.actual_departure,
        scheduledArrival: flight.scheduled_arrival,
        estimatedArrival: flight.estimated_arrival,
        actualArrival: flight.actual_arrival,
        status: flight.status,
        delayMinutes: Number(flight.delay_minutes ?? 0),
        riskScore,
        riskLevel,
        gate: flight.gate,
        terminal: flight.terminal,
      };
    });

    console.log('[Flight Operations] Flights loaded from FastAPI:', flights);
    return flights;
  } catch (error) {
    console.error('[Flight Operations] Failed to fetch flights:', error);
    // Do not silently substitute demo flights for backend records.
    throw error;
  }
};

// ============================================================
// GET DYNAMIC OPERATIONAL PULSE FROM FASTAPI
// ============================================================

export const getOperationalPulse = async () => {
  try {
    const [pulseResponse, flightsResponse] = await Promise.all([
      apiClient.get("/api/flights/operational-pulse"),
      apiClient.get("/api/flights/"),
    ]);

    const pulse = pulseResponse.data;
    const flights = flightsResponse.data;

    if (!Array.isArray(flights)) {
      throw new Error("Invalid flight data received");
    }

    const totalFlights = Number(pulse.total_flights ?? 0);

    const highRiskFlights = flights.filter((flight) => {
      const score = Number(flight.risk_score ?? 0);
      return score >= 50 && score < 75;
    }).length;

    const onTimeFlights = flights.filter((flight) => {
      const delay = Number(flight.delay_minutes ?? 0);
      return delay <= 15;
    }).length;

    const onTimePercentage =
      totalFlights > 0
        ? Number(
            ((onTimeFlights / totalFlights) * 100).toFixed(1)
          )
        : null;

    return {
      totalMonitoredFlights: totalFlights,

      criticalRiskFlights: Number(
        pulse.critical_risk_flights ?? 0
      ),

      highRiskFlights,

      onTimePercentage,

      networkAverageDelayMinutes: Number(
        pulse.average_delay_minutes ?? 0
      ),

      activeDisruptions: Number(
        pulse.delayed_flights ?? 0
      ),

      proactiveSavingsEst: null,

      hubStatus: {},
    };
  } catch (error) {
    console.error(
      "[Flight Operations] Operational Pulse API failed:",
      error
    );

    throw error;
  }
};

/**
 * Fetch risk score and risk factor breakdown for a specific flight
 * Endpoint: GET /flights/{flightNumber}/risk
 */
// ============================================================
// GET DYNAMIC FLIGHT RISK FROM FASTAPI
// ============================================================

export const getFlightRisk = async (flightId) => {
  try {
    const response = await apiClient.get(
      `/api/flights/${encodeURIComponent(flightId)}/risk`
    );

    const data = response.data;

    return {
      flightId: data.flight_id,

      flightNumber: data.flight_number,

      riskScore: Number(data.risk_score ?? 0),

      riskLevel: data.risk_level ?? "LOW",

      riskFactors: (data.risk_factors ?? []).map((factor) => ({
        id: factor.id,

        category: factor.factor_type
          ?.replaceAll("_", " ") ?? "OTHER",

        severity: factor.severity,

        score: Number(factor.score ?? 0),

        description: factor.description,
      })),
    };
  } catch (error) {
    console.error(
      `[Flight Operations] Failed to fetch risk for flight ${flightId}:`,
      error
    );

    throw error;
  }
};

/**
 * Fetch live delay details for a flight by numeric database ID.
 * Endpoint: GET /api/flights/{flight_id}
 * Note: the backend does not currently expose a delay reason.
 */
export const getFlightDelay = async (flightId) => {
  try {
    const numericFlightId = Number(flightId);

    if (!Number.isInteger(numericFlightId) || numericFlightId <= 0) {
      throw new Error("A valid numeric flight ID is required.");
    }

    const response = await apiClient.get(`/api/flights/${numericFlightId}`);
    const flight = response.data;

    return {
      flightId: flight.id,
      flightNumber: flight.flight_number,
      delayMinutes: Number(flight.delay_minutes ?? 0),
      delayReason: null,
      status: flight.status,
      origin: {
        code: flight.origin_code,
        name: flight.origin_name ?? flight.origin_code,
      },
      destination: {
        code: flight.destination_code,
        name: flight.destination_name ?? flight.destination_code,
      },
      scheduledDeparture: flight.scheduled_departure,
      estimatedDeparture: flight.estimated_departure,
      actualDeparture: flight.actual_departure,
    };
  } catch (error) {
    console.error(
      `[Flight Operations] Failed to fetch delay for flight ${flightId}:`,
      error
    );
    throw error;
  }
};

/**
 * Simulate what-if impact scenario given additional delay in minutes
 * Endpoint: POST /flights/{flightNumber}/simulate-impact
 * Body: { additionalDelay: number }
 */
// ============================================================
// SIMULATE FLIGHT IMPACT USING FASTAPI
// ============================================================

export const simulateFlightImpact = async (
  flightId,
  additionalDelay = 0
) => {
  try {
    const numericFlightId = Number(flightId);
    const delayMinutes = Number(additionalDelay);

    if (!Number.isInteger(numericFlightId) || numericFlightId <= 0) {
      throw new Error("A valid numeric flight ID is required.");
    }

    if (!Number.isFinite(delayMinutes) || delayMinutes < 0) {
      throw new Error("Additional delay must be a non-negative number.");
    }

    const response = await apiClient.post(
      "/api/flights/simulate-impact",
      {
        flight_id: numericFlightId,
        additional_delay_minutes: delayMinutes
      }
    );

    console.log(
      "[Flight Operations] Impact simulation result:",
      response.data
    );

    return response.data;

  } catch (error) {
    console.error(
      "[Flight Operations] Impact simulation failed:",
      error
    );

    throw error;
  }
};

/**
 * Fetch AI mitigation recommendation for a flight
 * Endpoint: GET /flights/{flightNumber}/recommendation
 */
export const getFlightRecommendation = async (flightNumber) => {
  if (USE_DEMO_DATA) {
    await demoDelay(200);
    const flight = localFlightsState.find(
      (f) => f.flightNumber.toLowerCase() === flightNumber.toLowerCase()
    );
    if (!flight) throw new Error(`Flight ${flightNumber} not found`);
    return flight.recommendation;
  }

  try {
    const response = await apiClient.get(
      `/flights/${encodeURIComponent(flightNumber)}/recommendation`
    );
    return response.data;
  } catch (error) {
    console.error(`[flightApi] Failed to fetch recommendation for ${flightNumber}:`, error);
    throw error;
  }
};

/**
 * Approve AI mitigation decision
 * Endpoint: POST /flights/{flightNumber}/approve
 * Body: { approvedBy: string }
 */
export const approveDecision = async (flightNumber, approvedBy = 'Operations Dispatcher') => {
  if (USE_DEMO_DATA) {
    await demoDelay(350);
    const flightIndex = localFlightsState.findIndex(
      (f) => f.flightNumber.toLowerCase() === flightNumber.toLowerCase()
    );
    if (flightIndex === -1) throw new Error(`Flight ${flightNumber} not found`);

    const now = new Date().toISOString();
    localFlightsState[flightIndex].recommendation = {
      ...localFlightsState[flightIndex].recommendation,
      status: 'APPROVED',
      approvedBy,
      timestamp: now
    };

    // Reflect approval in agent workflow
    if (Array.isArray(localFlightsState[flightIndex].agentWorkflow)) {
      const lastWorkflow = localFlightsState[flightIndex].agentWorkflow[localFlightsState[flightIndex].agentWorkflow.length - 1];
      if (lastWorkflow) {
        lastWorkflow.status = 'COMPLETED';
        lastWorkflow.detail = `Approved by ${approvedBy} at ${now.substring(11, 19)} UTC`;
      }
    }

    return {
      success: true,
      message: `Recommendation for ${flightNumber} successfully approved.`,
      flightNumber,
      approvedBy,
      status: 'APPROVED',
      timestamp: now
    };
  }

  try {
    const response = await apiClient.post(
      `/flights/${encodeURIComponent(flightNumber)}/approve`,
      { approvedBy }
    );
    return response.data;
  } catch (error) {
    console.error(`[flightApi] Failed to approve decision for ${flightNumber}:`, error);
    throw error;
  }
};

/**
 * Escalate/Review decision for secondary flight controller evaluation
 * Endpoint: POST /flights/{flightNumber}/review
 * Body: { reviewedBy: string }
 */
export const reviewDecision = async (flightNumber, reviewedBy = 'Senior Operations Lead') => {
  if (USE_DEMO_DATA) {
    await demoDelay(350);
    const flightIndex = localFlightsState.findIndex(
      (f) => f.flightNumber.toLowerCase() === flightNumber.toLowerCase()
    );
    if (flightIndex === -1) throw new Error(`Flight ${flightNumber} not found`);

    const now = new Date().toISOString();
    localFlightsState[flightIndex].recommendation = {
      ...localFlightsState[flightIndex].recommendation,
      status: 'REVIEW_REQUESTED',
      reviewedBy,
      timestamp: now
    };

    return {
      success: true,
      message: `Decision review requested for flight ${flightNumber}. Escrow notification sent.`,
      flightNumber,
      reviewedBy,
      status: 'REVIEW_REQUESTED',
      timestamp: now
    };
  }

  try {
    const response = await apiClient.post(
      `/flights/${encodeURIComponent(flightNumber)}/review`,
      { reviewedBy }
    );
    return response.data;
  } catch (error) {
    console.error(`[flightApi] Failed to request review for ${flightNumber}:`, error);
    throw error;
  }
};

// ============================================================
// GET FLIGHT DEPENDENCIES FROM FASTAPI
// ============================================================

export const getFlightDependencies = async (flightId) => {
  if (!Number.isInteger(Number(flightId)) || Number(flightId) <= 0) {
    throw new Error("A valid flight ID is required.");
  }

  try {
    const response = await apiClient.get(
      `/api/flights/${encodeURIComponent(flightId)}/dependencies`
    );

    if (!Array.isArray(response.data)) {
      throw new Error("Invalid dependency response from FastAPI.");
    }

    return response.data.map((dependency) => ({
      id: dependency.id,
      flightId: dependency.flight_id,
      dependentFlightId: dependency.dependent_flight_id,
      dependentFlightNumber:
        dependency.dependent_flight_number ?? "Unknown",
      dependentFlightStatus:
        dependency.dependent_flight_status ?? "UNKNOWN",
      dependencyType: dependency.dependency_type,
      minimumTurnaroundMinutes:
        Number(dependency.minimum_turnaround_minutes ?? 0),
    }));
  } catch (error) {
    console.error(
      `[Flight Operations] Failed to load dependencies for flight ${flightId}:`,
      error
    );

    throw error;
  }
};


// Live Gemini/LangGraph planning. Advisory only; no approval or execution.
// Compatible with AIRecommendation.jsx: generateAIPlanning(flight, { runwayCode }).
export const generateAIPlanning = async (flight, options = {}) => {
  const flightNumber = flight?.flightNumber ?? flight?.flight_number;
  const airport = flight?.origin?.code ?? flight?.origin_code;

  if (!flightNumber || !airport) {
    throw new Error('Flight number and origin airport are required for AI planning.');
  }

  const delay = Number(flight?.delayMinutes ?? flight?.delay_minutes ?? 0);
  const disruption = delay > 0
    ? `Flight ${flightNumber} is delayed by ${delay} minutes; assess operational impacts and next steps.`
    : `Review operational readiness and potential disruptions for flight ${flightNumber}.`;

  const runwayCode = options?.runwayCode?.trim().toUpperCase() || null;
  if (runwayCode && (runwayCode.length < 2 || runwayCode.length > 10)) {
    throw new Error('Runway code must contain 2–10 characters.');
  }

  const response = await apiClient.post('/api/ai/planning', {
    airport,
    disruption,
    affected_flights: [flightNumber],
    gate_request: null,
    runway_code: runwayCode,
  });

  return response.data;
};
