# raritan.xerus

Ansible Collection for managing Raritan PDU and other devices.

## Requirements

- Python >= 3.9
- `raritan` pip package >= 4.3.0

## Installation

    ansible-galaxy collection install raritan.xerus

Install Python dependency:

    pip install raritan>=4.3.0

## Modules

- `raritan.xerus.pdu_config` — Configure PDU-wide settings
- `raritan.xerus.outlet_config` — Configure individual outlets and control power state

## Example

    - name: Set PDU name
      raritan.xerus.pdu_config:
        host: 192.168.1.100
        username: admin
        password: secret
        validate_certs: false
        name: "Server Room PDU-1"

    - name: Power on outlet 3
      raritan.xerus.outlet_config:
        host: 192.168.1.100
        username: admin
        password: secret
        validate_certs: false
        outlet: 3
        name: "Web Server"
        state: on
