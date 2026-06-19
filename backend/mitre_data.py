"""Static MITRE ATT&CK matrix subset relevant to authentication/SOC use cases."""

TACTICS = [
    {
        "id": "TA0001",
        "name": "Initial Access",
        "techniques": [
            {"id": "T1078", "name": "Valid Accounts"},
            {"id": "T1133", "name": "External Remote Services"},
            {"id": "T1190", "name": "Exploit Public-Facing Application"},
        ],
    },
    {
        "id": "TA0006",
        "name": "Credential Access",
        "techniques": [
            {"id": "T1110", "name": "Brute Force"},
            {"id": "T1110.001", "name": "Password Guessing"},
            {"id": "T1110.003", "name": "Password Spraying"},
            {"id": "T1110.004", "name": "Credential Stuffing"},
            {"id": "T1555", "name": "Credentials from Password Stores"},
        ],
    },
    {
        "id": "TA0005",
        "name": "Defense Evasion",
        "techniques": [
            {"id": "T1078", "name": "Valid Accounts"},
            {"id": "T1036", "name": "Masquerading"},
        ],
    },
    {
        "id": "TA0008",
        "name": "Lateral Movement",
        "techniques": [
            {"id": "T1021", "name": "Remote Services"},
            {"id": "T1021.001", "name": "RDP"},
            {"id": "T1021.004", "name": "SSH"},
        ],
    },
    {
        "id": "TA0009",
        "name": "Collection",
        "techniques": [
            {"id": "T1213", "name": "Data from Information Repositories"},
        ],
    },
    {
        "id": "TA0010",
        "name": "Exfiltration",
        "techniques": [
            {"id": "T1041", "name": "Exfiltration Over C2 Channel"},
        ],
    },
]
