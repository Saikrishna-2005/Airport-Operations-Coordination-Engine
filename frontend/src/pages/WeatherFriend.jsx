import { useCallback, useEffect, useState } from 'react';
import api from '../api';
import './Weather.scoped.css';

// Preserve the existing sample-flight mapping when these airports are monitored.
const sampleAirportIds = { HYD: 'hyderabad', VGA: 'vijayawada', MAA: 'chennai' };

function mapMonitoredAirport(item) {
  return {
    id: sampleAirportIds[item.airport_code] || item.airport_code.toLowerCase(),
    name: item.airport_name || item.airport_code,
    shortName: item.airport_code,
    latitude: item.latitude,
    longitude: item.longitude,
  };
}

const initialFlights = [
  {
    id: 'AI 502',
    from: 'Hyderabad',
    to: 'Delhi',
    status: 'Delayed',
    cause: 'Weather monitoring',
    airportId: 'hyderabad',
  },
  {
    id: '6E 214',
    from: 'Chennai',
    to: 'Bengaluru',
    status: 'Monitoring',
    cause: 'Rain monitoring',
    airportId: 'chennai',
  },
  {
    id: 'UK 830',
    from: 'Mumbai',
    to: 'Hyderabad',
    status: 'On Schedule',
    cause: 'Routine monitoring',
    airportId: 'hyderabad',
  },
];

function getWeatherDescription(code) {
  if (code === 0) return 'Clear Sky';
  if ([1, 2, 3].includes(code)) return 'Partly Cloudy';
  if ([45, 48].includes(code)) return 'Fog';
  if ([51, 53, 55, 56, 57].includes(code)) return 'Drizzle';
  if ([61, 63, 65, 66, 67, 80, 81, 82].includes(code)) return 'Rain';
  if ([71, 73, 75, 77, 85, 86].includes(code)) return 'Snow';
  if ([95, 96, 99].includes(code)) return 'Thunderstorm';
  return 'Clear Sky';
}

function getWeatherIcon(code) {
  if (code === 0) return '☀️';
  if ([1, 2, 3].includes(code)) return '⛅';
  if ([45, 48].includes(code)) return '🌫️';
  if ([51, 53, 55, 56, 57].includes(code)) return '🌦️';
  if ([61, 63, 65, 66, 67, 80, 81, 82].includes(code)) return '🌧️';
  if ([71, 73, 75, 77, 85, 86].includes(code)) return '❄️';
  if ([95, 96, 99].includes(code)) return '⛈️';
  return '☀️';
}

// Map the backend Rule Engine response to the existing alert-card UI.
// LOW with zero triggered rules is a normal assessment, not an alert.
function createRuleEngineAlert(airport, response, weatherCard) {
  const risk = response?.risk;
  if (!risk || !['LOW', 'MEDIUM', 'HIGH'].includes(risk.risk_level)) {
    throw new Error('Invalid risk response from backend');
  }
  if (!Number.isInteger(risk.triggered_rules) || !Array.isArray(risk.messages)) {
    throw new Error('Incomplete risk response from backend');
  }
  if (risk.triggered_rules === 0) return null;

  const severity = risk.risk_level.charAt(0) + risk.risk_level.slice(1).toLowerCase();
  return {
    id: `rule-${airport.id}`,
    airportId: airport.id,
    airportName: airport.name,
    airportCode: airport.shortName,
    severity,
    title: `${severity} Weather Risk (Advisory)`,
    message: risk.messages.join(' '),
    condition: weatherCard?.condition ?? 'Unavailable',
    windSpeed: response.weather?.wind_speed_kmh ?? undefined,
    source: 'Python Weather Rule Engine',
    triggeredRules: risk.triggered_rules,
  };
}

function App() {
  // SQLite is the source of truth for the shared monitored-airport list.
  const [airports, setAirports] = useState([]);
  const [airportsLoading, setAirportsLoading] = useState(true);

  const flights = initialFlights;
  const [selectedSeverity, setSelectedSeverity] = useState('All');
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [weather, setWeather] = useState([]);
  const [liveWeatherAlerts, setLiveWeatherAlerts] = useState([]);
  const [riskAssessments, setRiskAssessments] = useState({});
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [weatherError, setWeatherError] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);

  // Airport code entered by the user
  const [airportSearch, setAirportSearch] = useState('');
  const [airportMatches, setAirportMatches] = useState([]);
  const [airportSearchLoading, setAirportSearchLoading] = useState(false);
  const [airportSearchError, setAirportSearchError] = useState('');
  const [selectedAirport, setSelectedAirport] = useState(null);

  // Airport management request state
  const [airportSaving, setAirportSaving] = useState(false);

  // Error or success message for airport management
  const [airportMessage, setAirportMessage] = useState('');

  const loadMonitoredAirports = useCallback(async () => {
    try {
      const response = await api.get('/weather/airports');
      if (!response.data?.success || !Array.isArray(response.data.airports)) {
        throw new Error('Invalid airport list response');
      }
      setAirports(response.data.airports.map(mapMonitoredAirport));
      return true;
    } catch (error) {
      console.error('Load monitored airports error:', error);
      setAirportMessage('Unable to load monitored airports. Check your login and backend connection.');
      return false;
    } finally {
      setAirportsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMonitoredAirports();
  }, [loadMonitoredAirports]);

  const fetchWeather = useCallback(async (currentAirports) => {
    if (!currentAirports?.length) {
      setWeather([]);
      setLiveWeatherAlerts([]);
      setRiskAssessments({});
      setLastUpdated(null);
      setWeatherError('');
      return;
    }

    setWeatherLoading(true);
    setWeatherError('');

    try {
      // Weather cards and Rule Engine assessments are independent:
      // a risk API failure never hides otherwise valid weather data.
      const results = await Promise.all(
        currentAirports.map(async (airport) => {
          const code = encodeURIComponent(airport.shortName);
          const [weatherResult, riskResult] = await Promise.allSettled([
            api.get(`/weather/current/${code}`),
            api.get(`/weather/risk/${code}`),
          ]);
          return { airport, weatherResult, riskResult };
        })
      );

      const weatherCards = [];
      const ruleAlerts = [];
      const errors = [];
      const assessments = {};

      const errorMessage = (error) => {
        const detail = error?.response?.data?.detail;
        if (typeof detail === 'string') return detail;
        if (detail && typeof detail.message === 'string') return detail.message;
        return error?.message || 'Service unavailable';
      };

      results.forEach(({ airport, weatherResult, riskResult }) => {
        let card = null;
        if (weatherResult.status === 'fulfilled' && weatherResult.value.data?.success) {
          const current = weatherResult.value.data;
          card = {
            ...airport,
            temperature: current.temperature_c == null ? null : Math.round(current.temperature_c),
            feelsLike: current.apparent_temperature_c ?? null,
            humidity: current.humidity_percent ?? null,
            windSpeed: current.wind_speed_kmh ?? null,
            weatherCode: current.weather_code ?? null,
            condition: current.weather_code == null ? 'Unavailable' : getWeatherDescription(current.weather_code),
            icon: current.weather_code == null ? '—' : getWeatherIcon(current.weather_code),
          };
          weatherCards.push(card);
        } else {
          errors.push(`${airport.shortName} weather: ${weatherResult.status === 'rejected' ? errorMessage(weatherResult.reason) : 'Invalid response'}`);
        }

        if (riskResult.status === 'fulfilled' && riskResult.value.data?.success) {
          try {
            const riskResponse = riskResult.value.data;

            const alert = createRuleEngineAlert(
              airport,
              riskResponse,
              card
            );

            // Store successful backend assessments,
            // including LOW risk with zero triggered rules.
            assessments[airport.shortName] = riskResponse.risk;

            if (alert) {
              ruleAlerts.push(alert);
            }
          } catch (error) {
            errors.push(`${airport.shortName} risk: ${error.message}`);
          }
        }else {
                  errors.push(`${airport.shortName} risk: ${riskResult.status === 'rejected' ? errorMessage(riskResult.reason) : 'Invalid response'}`);
          }
      });

      setWeather(weatherCards);
      setLiveWeatherAlerts(ruleAlerts);
      setRiskAssessments(assessments);
      setLastUpdated(weatherCards.length ? new Date() : null);
      setWeatherError(errors.length ? `Some data unavailable: ${errors.join('; ')}` : '');
    } catch (error) {
      console.error('Weather and risk API error:', error);
      setWeather([]);
      setLiveWeatherAlerts([]);
      setRiskAssessments({});
      setLastUpdated(null);
      setWeatherError('Unable to retrieve weather and risk data from the backend.');
    } finally {
      setWeatherLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!airportsLoading) fetchWeather(airports);
  }, [fetchWeather, airports, airportsLoading]);

  // Debounced search. Abort stale requests when the user changes the query.
  useEffect(() => {
    const query = airportSearch.trim();
    if (selectedAirport || query.length < 2) {
      setAirportMatches([]);
      setAirportSearchLoading(false);
      setAirportSearchError('');
      return;
    }

    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setAirportSearchLoading(true);
      setAirportSearchError('');
      try {
        const response = await api.get('/weather/airports/search', {
          params: { q: query, limit: 15 },
          signal: controller.signal,
        });
        if (!response.data?.success || !Array.isArray(response.data.airports)) {
          throw new Error('Invalid airport search response');
        }
        setAirportMatches(response.data.airports);
      } catch (error) {
        if (controller.signal.aborted || error.code === 'ERR_CANCELED') return;
        console.error('Airport search error:', error);
        setAirportMatches([]);
        setAirportSearchError('Airport search unavailable. Check your login and backend connection.');
      } finally {
        if (!controller.signal.aborted) setAirportSearchLoading(false);
      }
    }, 300);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [airportSearch, selectedAirport]);

  const chooseAirport = (airport) => {
    setSelectedAirport(airport);
    setAirportSearch(`${airport.airport_code} — ${airport.name}`);
    setAirportMatches([]);
    setAirportSearchError('');
    setAirportMessage('');
  };

  const handleAddAirport = async (e) => {
    e.preventDefault();
    const code = selectedAirport?.airport_code || '';
    if (!/^[A-Z]{3}$/.test(code)) {
      setAirportMessage('Search for an airport and select it from the results.');
      return;
    }
    if (airportSaving) return;
    setAirportSaving(true);
    setAirportMessage('');
    try {
      const response = await api.post('/weather/airports', { airport_code: code });
      if (!response.data?.success) throw new Error('Unable to add airport.');
      setSelectedAirport(null);
      setAirportSearch('');
      setAirportMatches([]);
      const loaded = await loadMonitoredAirports();
      if (loaded) setAirportMessage(`Airport ${code} added successfully.`);
    } catch (error) {
      console.error('Add airport error:', error);
      const detail = error.response?.data?.detail;
      setAirportMessage(typeof detail === 'string' ? detail : 'Unable to add airport. Please try again.');
    } finally {
      setAirportSaving(false);
    }
  };

  const handleDeleteAirport = async (airportId) => {
    const airport = airports.find((item) => item.id === airportId);
    if (!airport || airportSaving) return;
    setAirportSaving(true);
    setAirportMessage('');
    try {
      await api.delete(`/weather/airports/${encodeURIComponent(airport.shortName)}`);
      const loaded = await loadMonitoredAirports();
      if (loaded) setAirportMessage(`Airport ${airport.shortName} removed successfully.`);
    } catch (error) {
      console.error('Remove airport error:', error);
      const detail = error.response?.data?.detail;
      setAirportMessage(typeof detail === 'string' ? detail : 'Unable to remove airport. Please try again.');
    } finally {
      setAirportSaving(false);
    }
  };

  // Only backend Rule Engine assessments with triggered rules are alerts.
  // Demo alerts are intentionally excluded from live monitoring.
  const allAlerts = liveWeatherAlerts;

  const filteredAlerts =
    selectedSeverity === 'All'
      ? allAlerts
      : allAlerts.filter((alert) => alert.severity === selectedSeverity);

  function getFlightWeatherImpact(flight) {
    const airport = airports.find(
      (item) => item.id === flight.airportId
    );

    if (!airport) {
      return {
        label: 'Airport Unavailable',
        severity: 'normal',
      };
    }

    const risk = riskAssessments[airport.shortName];

    if (!risk) {
      return {
        label: `Risk Unavailable · ${airport.shortName}`,
        severity: 'normal',
      };
    }

    switch (risk.risk_level) {
      case 'HIGH':
        return {
          label: 'HIGH Risk (Advisory)',
          severity: 'high',
        };

      case 'MEDIUM':
        return {
          label: 'MEDIUM Risk (Advisory)',
          severity: 'medium',
        };

      case 'LOW':
        return {
          label:
            risk.triggered_rules === 0
              ? 'LOW Risk · No Rules Triggered'
              : 'LOW Risk (Advisory)',
          severity: 'low',
        };

      default:
        return {
          label: 'Risk Unavailable',
          severity: 'normal',
        };
    }
  }

  function openAlertDetails(alert) {
    setSelectedAlert(alert);
  }

  const highAlerts = liveWeatherAlerts.filter(
    (alert) => alert.severity === 'High'
  ).length;

  return (
  <div className="weather-module">
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-icon">✈</span>
          <div>
            <h1>SkyOps</h1>
            <p>Airport Operations Coordination Engine</p>
          </div>
        </div>

        <div className="topbar-right">
          <span className="live-indicator">
            <span className="live-dot" />
            Weather Monitoring
          </span>
          <button
            className="refresh-button"
            onClick={() => fetchWeather(airports)}
            disabled={weatherLoading}
          >
            {weatherLoading ? '⟳ Refreshing...' : '↻ Refresh Weather'}
          </button>
        </div>
      </header>

      <main className="dashboard">
        <section className="welcome-section">
          <div>
            <p className="eyebrow">OPERATIONS OVERVIEW</p>
            <h2>Airport Operations Dashboard</h2>
            <p className="subtitle">
              Monitor airport weather conditions and their potential operational impact.
            </p>
          </div>
          <div className="updated-time">
            <span>Last updated</span>
            <strong>
              {lastUpdated ? lastUpdated.toLocaleTimeString() : 'Waiting for data'}
            </strong>
          </div>
        </section>

        {weatherError && (
          <div className="error-message">
            <strong>Notice:</strong> {weatherError}
          </div>
        )}

        <section className="stats-grid">
          <div className="stat-card">
            <span className="stat-icon blue">✈</span>
            <div>
              <p>Flights Monitored</p>
              <h3>{flights.length}</h3>
              <span className="stat-note">Sample flight records</span>
            </div>
          </div>

          <div className="stat-card">
            <span className="stat-icon red">⚠</span>
            <div>
              <p>High Weather Alerts</p>
              <h3>{highAlerts}</h3>
              <span className="stat-note">Backend Rule Engine · advisory</span>
            </div>
          </div>

          <div className="stat-card">
            <span className="stat-icon green">◉</span>
            <div>
              <p>Airports Monitored</p>
              <h3>{airports.length}</h3>
              <span className="stat-note">Worldwide IATA airport monitoring</span>
            </div>
          </div>

          <div className="stat-card">
            <span className="stat-icon orange">↻</span>
            <div>
              <p>Flights Mapped</p>
              <h3>{flights.length}</h3>
              <span className="stat-note">Linked to airport weather</span>
            </div>
          </div>
        </section>

        <section className="section" style={{ background: '#f8fafc', padding: '20px', borderRadius: '12px', border: '1px solid #e2e8f0', marginBottom: '24px' }}>
          <div className="section-heading" style={{ marginBottom: '12px' }}>
            <div>
              <p className="eyebrow">CONFIGURATION</p>
              <h2>Add Airport for Monitoring</h2>
            </div>
          </div>
          <form onSubmit={handleAddAirport} style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'end' }}>
            <div style={{ flex: '1 1 280px', position: 'relative' }}>
              <label htmlFor="monitor-airport-search" style={{ display: 'block', fontSize: '12px', fontWeight: '600', marginBottom: '4px' }}>
                Search airport by name, city, country code, or IATA code
              </label>
              <input
                id="monitor-airport-search"
                type="search"
                autoComplete="off"
                placeholder="e.g. Chennai, London, JFK, IN"
                value={airportSearch}
                onChange={(event) => {
                  setAirportSearch(event.target.value);
                  setSelectedAirport(null);
                  setAirportMessage('');
                }}
                aria-controls="airport-search-results"
                aria-expanded={airportMatches.length > 0}
                style={{ width: '100%', padding: '9px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
              />
              {airportSearchLoading && <p style={{ fontSize: '12px', marginTop: '6px' }}>Searching airports...</p>}
              {airportSearchError && <p role="alert" style={{ color: '#b91c1c', fontSize: '12px' }}>{airportSearchError}</p>}
              {!airportSearchLoading && !airportSearchError && !selectedAirport && airportSearch.trim().length >= 2 && airportMatches.length === 0 && (
                <p style={{ fontSize: '12px', marginTop: '6px' }}>No matching airports found.</p>
              )}
              {airportMatches.length > 0 && !selectedAirport && (
                <div id="airport-search-results" role="listbox" aria-label="Matching airports" style={{ position: 'absolute', zIndex: 20, top: '100%', left: 0, right: 0, maxHeight: '260px', overflowY: 'auto', background: '#fff', border: '1px solid #cbd5e1', borderRadius: '6px', boxShadow: '0 8px 18px rgba(0,0,0,0.12)' }}>
                  {airportMatches.map((airport) => (
                    <button
                      key={airport.airport_code}
                      type="button"
                      role="option"
                      aria-selected={false}
                      onClick={() => chooseAirport(airport)}
                      style={{ display: 'block', width: '100%', textAlign: 'left', padding: '10px 12px', background: '#fff', border: 0, borderBottom: '1px solid #e2e8f0', cursor: 'pointer', color: '#0f172a' }}
                    >
                      <strong>{airport.airport_code} — {airport.name}</strong>
                      <span style={{ display: 'block', fontSize: '12px', color: '#475569' }}>{airport.city}, {airport.country}</span>
                    </button>
                  ))}
                </div>
              )}
              {selectedAirport && (
                <p style={{ marginTop: '8px', fontSize: '13px', color: '#166534' }}>
                  Selected: <strong>{selectedAirport.airport_code} — {selectedAirport.name}</strong> ({selectedAirport.city}, {selectedAirport.country})
                </p>
              )}
            </div>
            <button type="submit" className="refresh-button" disabled={airportSaving || airportsLoading || !selectedAirport} style={{ height: '38px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '600' }}>
              {airportSaving ? 'Saving...' : '+ Add Airport'}
            </button>
          </form>
          <p style={{ marginTop: '8px', fontSize: '12px' }}>Type at least 2 characters, select an airport from the list, then click Add Airport. Coordinates are detected automatically.</p>
          {airportMessage && <p role="status" style={{ marginTop: '8px' }}>{airportMessage}</p>}
        </section>

        <section className="section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">LIVE CONDITIONS</p>
              <h2>Airport Weather</h2>
            </div>
            <span className="section-meta">
              {weatherLoading ? 'Updating weather...' : 'Powered by Open-Meteo'}
            </span>
          </div>

          <div className="weather-grid">
            {weather.length > 0
              ? weather.map((airport) => (
                  <article className="weather-card" key={airport.id}>
                    <button
                      className="delete-card-btn"
                      onClick={() => handleDeleteAirport(airport.id)}
                      disabled={airportSaving}
                      title="Remove Airport"
                    >
                      ×
                    </button>
                    <div className="weather-card-top">
                      <div>
                        <p className="airport-code">{airport.shortName}</p>
                        <h3>{airport.name}</h3>
                      </div>
                      <span className="weather-icon">{airport.icon}</span>
                    </div>

                    <div className="temperature-row">
                      <h2>{airport.temperature == null ? 'N/A' : `${airport.temperature}°C`}</h2>
                      <span>{airport.condition}</span>
                    </div>

                    <div className="weather-details">
                      <div>
                        <span>Feels like</span>
                        <strong>{airport.feelsLike == null ? 'N/A' : `${airport.feelsLike}°C`}</strong>
                      </div>
                      <div>
                        <span>Humidity</span>
                        <strong>{airport.humidity == null ? 'N/A' : `${airport.humidity}%`}</strong>
                      </div>
                      <div>
                        <span>Wind</span>
                        <strong>{airport.windSpeed == null ? 'N/A' : `${airport.windSpeed} km/h`}</strong>
                      </div>
                    </div>
                  </article>
                ))
              : airports.map((airport) => (
                  <article className="weather-card" key={airport.id}>
                    <button className="delete-card-btn" onClick={() => handleDeleteAirport(airport.id)} disabled={airportSaving} title="Remove Airport">×</button>
                    <div className="weather-card-top">
                      <div>
                        <p className="airport-code">{airport.shortName}</p>
                        <h3>{airport.name}</h3>
                      </div>
                      <span className="weather-icon">—</span>
                    </div>
                    <div className="temperature-row">
                      <h2>{weatherLoading ? '...' : 'Unavailable'}</h2>
                      <span>{weatherLoading ? 'Loading live weather' : 'No live data'}</span>
                    </div>
                  </article>
                ))}
          </div>
        </section>

        <section className="section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">AUTOMATED MONITORING</p>
              <h2>Weather Alerts</h2>
            </div>
            <span className="alert-count">{filteredAlerts.length} alerts</span>
          </div>

          <div className="severity-filters">
            {['All', 'High', 'Medium', 'Low'].map((severity) => (
              <button
                key={severity}
                className={`filter-button ${
                  selectedSeverity === severity ? 'active' : ''
                }`}
                onClick={() => setSelectedSeverity(severity)}
              >
                {severity}
              </button>
            ))}
          </div>

          {filteredAlerts.length === 0 ? (
            <div className="empty-state">
              <span>✓</span>
              <h3>No alerts found for this severity</h3>
              <p>No backend rules triggered for this filter, or risk data is unavailable. Check notices above.</p>
            </div>
          ) : (
            <div className="alerts-list">
              {filteredAlerts.map((alert) => (
                <article
                  className={`alert-card severity-${alert.severity.toLowerCase()}`}
                  key={alert.id}
                >
                  <div className="alert-symbol">⚠</div>
                  <div className="alert-content">
                    <div className="alert-title-row">
                      <h3>{alert.title}</h3>
                      <span
                        className={`severity-badge ${alert.severity.toLowerCase()}`}
                      >
                        {alert.severity}
                      </span>
                    </div>
                    <p>{alert.message}</p>
                    <div className="alert-meta">
                      <span>📍 {alert.airportCode} · {alert.airportName}</span>
                      <span>Source: {alert.source}</span>
                    </div>
                  </div>
                  <button
                    className="details-button"
                    onClick={() => openAlertDetails(alert)}
                  >
                    View Details
                  </button>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">OPERATIONAL COORDINATION</p>
              <h2>Flight Operations</h2>
            </div>
            <span className="section-meta">Airport weather mapping</span>
          </div>

          <div className="table-note">
            Flight routes and statuses below are sample records. Weather impact
            is based on available backend Rule Engine alerts for each mapped airport;
            this is not a live airline flight feed. Missing risk assessments do not mean safe conditions.
          </div>

          <div className="table-container">
            <table className="flights-table">
              <thead>
                <tr>
                  <th>Flight</th>
                  <th>Route</th>
                  <th>Status</th>
                  <th>Mapped Airport</th>
                  <th>Weather Impact</th>
                  <th>Cause</th>
                </tr>
              </thead>
              <tbody>
                {flights.map((flight) => {
                  const airport = airports.find(
                    (item) => item.id === flight.airportId
                  );
                  const impact = getFlightWeatherImpact(flight);

                  return (
                    <tr key={flight.id}>
                      <td>
                        <strong>{flight.id}</strong>
                      </td>
                      <td>{flight.from} → {flight.to}</td>
                      <td>
                        <span
                          className={`flight-status ${flight.status
                            .toLowerCase()
                            .replaceAll(' ', '-')}`}
                        >
                          {flight.status}
                        </span>
                      </td>
                      <td>
                        <strong>{airport?.shortName ?? 'N/A'}</strong>
                        <span className="airport-cell-name">
                          {airport?.name ?? 'Unknown airport'}
                        </span>
                      </td>
                      <td>
                        <span className={`impact-badge ${impact.severity}`}>
                          {impact.label}
                        </span>
                      </td>
                      <td>{flight.cause}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>

        <footer className="dashboard-footer">
          <p>SkyOps · Airport Operations Coordination Engine</p>
          <p>Weather: Open-Meteo via FastAPI · Risk: Python Rule Engine (advisory) · Flights: sample</p>
        </footer>
      </main>

      {selectedAlert && (
        <div
          className="modal-overlay"
          onClick={() => setSelectedAlert(null)}
          role="presentation"
        >
          <section
            className="details-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="alert-details-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <p className="eyebrow">ALERT INFORMATION</p>
                <h2 id="alert-details-title">{selectedAlert.title}</h2>
              </div>
              <button
                className="modal-close"
                onClick={() => setSelectedAlert(null)}
                aria-label="Close alert details"
              >
                ×
              </button>
            </div>

            <span
              className={`severity-badge ${selectedAlert.severity.toLowerCase()}`}
            >
              {selectedAlert.severity} Priority
            </span>

            <p className="modal-message">{selectedAlert.message}</p>

            <div className="modal-info-grid">
              <div>
                <span>Airport</span>
                <strong>{selectedAlert.airportName}</strong>
              </div>
              <div>
                <span>Airport Code</span>
                <strong>{selectedAlert.airportCode}</strong>
              </div>
              <div>
                <span>Weather Condition</span>
                <strong>{selectedAlert.condition}</strong>
              </div>
              <div>
                <span>Data Source</span>
                <strong>{selectedAlert.source}</strong>
              </div>
              {selectedAlert.windSpeed !== undefined && (
                <div>
                  <span>Wind Speed</span>
                  <strong>{selectedAlert.windSpeed} km/h</strong>
                </div>
              )}
            </div>

            <div className="affected-flights">
              <h3>Mapped Sample Flights</h3>
              {flights.filter(
                (flight) => flight.airportId === selectedAlert.airportId
              ).length > 0 ? (
                flights
                  .filter(
                    (flight) => flight.airportId === selectedAlert.airportId
                  )
                  .map((flight) => (
                    <div className="affected-flight-row" key={flight.id}>
                      <strong>{flight.id}</strong>
                      <span>{flight.from} → {flight.to}</span>
                    </div>
                  ))
              ) : (
                <p>No sample flights are mapped to this airport.</p>
              )}
            </div>

            <p className="modal-disclaimer">
              This alert is an automated weather indicator, not an official
              aviation warning. Confirm operational decisions with authorized
              airport and aviation sources.
            </p>

            <button
              className="refresh-button modal-done"
              onClick={() => setSelectedAlert(null)}
            >
              Close Details
            </button>
          </section>
        </div>
      )}
    </div>
  </div>
  );
}

export default App;