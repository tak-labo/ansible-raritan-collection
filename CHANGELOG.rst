======================================
taklabo.raritan_xerus Release Notes
======================================

.. contents:: Topics

v1.1.1
======

Minor Changes
-------------

- Documentation: Enhanced playbook and module_utils documentation for Galaxy and GitHub discoverability
  - Expanded README Playbooks section with detailed usage, parameters, and notes for each playbook
  - Added comprehensive header comments to all playbook files
  - Added docstrings to ``plugins/module_utils/raritan_client.py``

v1.1.0
======

New Modules
-----------

- ``taklabo.raritan_xerus.inlet_config`` - Configure inlet name and manage sensor alert thresholds
- ``taklabo.raritan_xerus.pdu_backup`` - Download and save a PDU configuration backup locally (raw or bulk format)

Minor Changes
-------------

- ``outlet_config`` - Added sensor alert threshold management (``sensor``, ``upper_critical``, ``upper_warning``, ``lower_warning``, ``lower_critical``, ``unset_thresholds``), mirroring ``inlet_config``
- ``inlet_config`` - Added ``unset_thresholds`` to disable a threshold without changing its stored value
- ``pdu_facts`` - Inlet facts now include voltage/current/active_power/apparent_power alert thresholds

Bugfixes
--------

- Pinned the ``raritan`` SDK dependency to ``4.3.13.52458`` to match tested PDU firmware. A newer SDK version declared schema fields the firmware didn't return, crashing ``pdu_facts`` and ``dns_config`` with ``KeyError`` on real hardware.

v1.0.1
======

- Renamed the collection namespace from ``tak_55`` to ``taklabo`` ahead of the first ``taklabo.raritan_xerus`` Galaxy publish.
- Fixed ``syslog_action``'s ``ACTION_TYPE``/argument keys.
- Added CI (pytest on push/PR) and declared ``pytest``/``raritan`` as project dev dependencies.

v1.0.0
======

New Modules
-----------

- ``taklabo.raritan_xerus.pdu_config`` - Configure PDU-wide settings (name, startup state, cycle delay)
- ``taklabo.raritan_xerus.outlet_config`` - Configure outlet settings and control power state (on/off/cycle)
- ``taklabo.raritan_xerus.snmp_config`` - Configure SNMP v2/v3 settings and system information
- ``taklabo.raritan_xerus.syslog_action`` - Manage syslog event engine actions
- ``taklabo.raritan_xerus.snmp_trap_action`` - Manage SNMP trap event engine actions
- ``taklabo.raritan_xerus.event_rule`` - Manage event engine rules
- ``taklabo.raritan_xerus.user_account`` - Manage user accounts and SNMPv3 settings
- ``taklabo.raritan_xerus.dns_config`` - Configure DNS servers and search suffixes
- ``taklabo.raritan_xerus.datetime_config`` - Configure NTP servers and timezone
- ``taklabo.raritan_xerus.pdu_facts`` - Gather PDU metadata, inlet and outlet sensor readings
