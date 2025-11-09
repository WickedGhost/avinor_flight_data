/*
 * Avinor Flight Card - renders a table of flights from the avinor_flight_data sensor attributes
 * Make available in HA card picker via window.customCards metadata.
 */

// Register metadata so the card shows up in the Lovelace card picker
// See: https://developers.home-assistant.io/docs/frontend/custom-ui/lovelace-custom-card/
try {
  window.customCards = window.customCards || [];
  const exists = window.customCards.some((c) => c.type === 'avinor-flight-card');
  if (!exists) {
    window.customCards.push({
      type: 'avinor-flight-card',
      name: 'Avinor Flight Card',
      description: 'Table of Avinor flights from sensor attributes (custom component).',
      preview: true,
      documentationURL: 'https://github.com/WickedGhost/avinor_flight_data',
    });
  }
} catch (e) {
  // non-fatal; HA will still allow manual YAML usage
}

class AvinorFlightCard extends HTMLElement {
  static getStubConfig(hass) {
    // Provide a simple default entity for preview/selection in the card picker
    if (hass && hass.states) {
      const firstSensor = Object.keys(hass.states).find((e) => e.startsWith('sensor.avinor_'));
      if (firstSensor) {
        return { entity: firstSensor, title: 'Avinor Flight Data' };
      }
    }
    return { entity: '', title: 'Avinor Flight Data' };
  }

  static getConfigElement() {
    return document.createElement('avinor-flight-card-editor');
  }

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
        <td style="padding: 8px;">${this._e(f.flightId)}</td>
        <td style="padding: 8px;">${this._e(f.dom_int)}</td>
        <td style="padding: 8px;">${this._e(f.schedule_time)}</td>
        <td style="padding: 8px;">${this._e(f.airport)}</td>
        <td style="padding: 8px;">${this._e(f.check_in)}</td>
        <td style="padding: 8px;">${this._e(f.gate)}</td>
        <td style="padding: 8px;">${this._e(f.status_code)}</td>
      </tr>
    `).join('');

    this._content.innerHTML = `
      <div style="margin-bottom:8px; font-size: 0.9em; color: var(--secondary-text-color);">${header}</div>
      <div style="overflow:auto;">
        <table style="width:100%; border-collapse: collapse;">
          <thead>
            <tr>
              <th style="text-align:left; padding: 8px; border-bottom: 1px solid var(--divider-color);">Flight</th>
              <th style="text-align:left; padding: 8px; border-bottom: 1px solid var(--divider-color);">Type</th>
              <th style="text-align:left; padding: 8px; border-bottom: 1px solid var(--divider-color);">Scheduled</th>
              <th style="text-align:left; padding: 8px; border-bottom: 1px solid var(--divider-color);">Airport</th>
              <th style="text-align:left; padding: 8px; border-bottom: 1px solid var(--divider-color);">Check-in</th>
              <th style="text-align:left; padding: 8px; border-bottom: 1px solid var(--divider-color);">Gate</th>
              <th style="text-align:left; padding: 8px; border-bottom: 1px solid var(--divider-color);">Status</th>
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

// Visual card editor for UI configuration
class AvinorFlightCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this.render();
  }

  configChanged(newConfig) {
    const event = new Event('config-changed', {
      bubbles: true,
      composed: true,
    });
    event.detail = { config: newConfig };
    this.dispatchEvent(event);
  }

  render() {
    if (!this._config) {
      return;
    }

    this.innerHTML = `
      <div style="padding: 16px;">
        <div style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 8px; font-weight: 500;">
            Entity (required)
          </label>
          <input
            type="text"
            id="entity"
            value="${this._config.entity || ''}"
            placeholder="sensor.avinor_osl_d"
            style="width: 100%; padding: 8px; border: 1px solid var(--divider-color); border-radius: 4px; background: var(--card-background-color); color: var(--primary-text-color);"
          />
          <div style="margin-top: 4px; font-size: 0.9em; color: var(--secondary-text-color);">
            Select an Avinor flight sensor entity
          </div>
        </div>

        <div style="margin-bottom: 16px;">
          <label style="display: block; margin-bottom: 8px; font-weight: 500;">
            Title (optional)
          </label>
          <input
            type="text"
            id="title"
            value="${this._config.title || ''}"
            placeholder="Avganger OSL"
            style="width: 100%; padding: 8px; border: 1px solid var(--divider-color); border-radius: 4px; background: var(--card-background-color); color: var(--primary-text-color);"
          />
          <div style="margin-top: 4px; font-size: 0.9em; color: var(--secondary-text-color);">
            Card title (leave empty for default)
          </div>
        </div>
      </div>
    `;

    // Add event listeners
    this.querySelector('#entity').addEventListener('input', (e) => {
      this._config = { ...this._config, entity: e.target.value };
      this.configChanged(this._config);
    });

    this.querySelector('#title').addEventListener('input', (e) => {
      this._config = { ...this._config, title: e.target.value };
      this.configChanged(this._config);
    });
  }

  set hass(hass) {
    this._hass = hass;
  }
}

customElements.define('avinor-flight-card-editor', AvinorFlightCardEditor);

// Log confirmation for debugging
console.info(
  '%c AVINOR-FLIGHT-CARD %c Registered successfully with visual editor ',
  'background-color: #41bdf5; color: #fff; font-weight: bold;',
  'background-color: #333; color: #fff;'
);
