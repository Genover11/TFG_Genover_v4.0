// web/static/js/main.js
document.addEventListener('DOMContentLoaded', function() {
    // Load vessels data
    const vesselsTable = document.getElementById('vessels-table');
    if (vesselsTable) {
        fetch('/api/v1/vessels/')
            .then(response => response.json())
            .then(data => {
                data.forEach(vessel => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td class="px-6 py-4">${vessel.name}</td>
                        <td class="px-6 py-4">${vessel.vessel_type || '-'}</td>
                        <td class="px-6 py-4">${vessel.position || '-'}</td>
                        <td class="px-6 py-4">${vessel.dwt || '-'}</td>
                    `;
                    vesselsTable.appendChild(row);
                });
            })
            .catch(error => console.error('Error:', error));
    }

    // Load cargoes data
    const cargoesTable = document.getElementById('cargoes-table');
    if (cargoesTable) {
        fetch('/api/v1/cargoes/')
            .then(response => response.json())
            .then(data => {
                data.forEach(cargo => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td class="px-6 py-4">${cargo.cargo_type}</td>
                        <td class="px-6 py-4">${cargo.quantity || '-'}</td>
                        <td class="px-6 py-4">${cargo.load_port || '-'} to ${cargo.discharge_port || '-'}</td>
                        <td class="px-6 py-4">${cargo.rate || '-'}</td>
                    `;
                    cargoesTable.appendChild(row);
                });
            })
            .catch(error => console.error('Error:', error));
    }
});