/*
 * Avinor Flight Card - renders a table of flights from the avinor_flight_data sensor attributes
 */

class AvinorFlightCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) {
      throw new Error('Please define entity');
    }
    this._config = config;
    this._content = document.createElement('div');
    this._content.style.padding = '16px';
    const card = document.createElement('ha-card');
    if (config.title) {
      card.header = config.title;
    } else {
      card.header = 'Avinor Flight Data';
    }
    card.appendChild(this._content);
    this.appendChild(card);
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._config) return;
    const entityId = this._config.entity;
    const state = hass.states[entityId];
    if (!state) {
      this._content.innerHTML = `<div>Entity ${entityId} not found</div>`;
      return;
    }
    const attrs = state.attributes || {};
    const flights = Array.isArray(attrs.flights) ? attrs.flights : [];

    const airport = attrs.airport || '';
    const direction = attrs.direction || '';
    const lastUpdate = attrs.last_update || '';

    const header = `Airport: ${airport} • Direction: ${direction} • Flights: ${flights.length} • Updated: ${lastUpdate}`;

    const rows = flights.map(f => `
      <tr>
        <td>${this._e(f.flightId)}</td>
        <td>${this._e(f.dom_int)}</td>
        <td>${this._e(f.schedule_time)}</td>
        <td>${this._e(f.airport)}</td>
        <td>${this._e(f.check_in)}</td>
        <td>${this._e(f.gate)}</td>
        <td>${this._e(f.status_code)}</td>
      </tr>
    `).join('');

    this._content.innerHTML = `
      <div style="margin-bottom:8px; font-size: 0.9em; color: var(--secondary-text-color);">${header}</div>
      <div style="overflow:auto;">
        <table style="width:100%; border-collapse: collapse;">
          <thead>
            <tr>
              <th style="text-align:left; padding: 8px; border-bottom: 1px solid var(--divider-color);">flightId</th>
              <th style="text-align:left; padding: 8px; border-bottom: 1px solid var(--divider-color);">dom_int</th>
              <th style="text-align:left; padding: 8px; border-bottom: 1px solid var(--divider-color);">schedule_time</th>
              <th style="text-align:left; padding: 8px; border-bottom: 1px solid var(--divider-color);">airport</th>
              <th style="text-align:left; padding: 8px; border-bottom: 1px solid var(--divider-color);">check_in</th>
              <th style="text-align:left; padding: 8px; border-bottom: 1px solid var(--divider-color);">gate</th>
              <th style="text-align:left; padding: 8px; border-bottom: 1px solid var(--divider-color);">status code</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>
      <div style="margin-top:8px; font-size: 0.8em; color: var(--secondary-text-color);">
        Flydata fra <a href="https://www.avinor.no/" target="_blank" rel="noreferrer">Avinor</a>
      </div>
    `;
  }

  _e(v) {
    if (v === undefined || v === null) return '';
    const s = String(v);
    // Basic HTML escaping to mitigate injection inside innerHTML usage.
    return s
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  getCardSize() {
    return 4;
  }
}

customElements.define('avinor-flight-card', AvinorFlightCard);
