#pragma once
// Copy to config.h locally; do not commit credentials.
const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* API_URL = "https://your-service.example";
const char* DEVICE_ID = "YOUR_CREATED_DEVICE_ID";
const char* DEVICE_KEY = "YOUR_ONE_TIME_DEVICE_KEY";
// Paste the root CA for your HTTPS host. Never use setInsecure().
const char* ROOT_CA = R"PEM(-----BEGIN CERTIFICATE-----
REPLACE_WITH_YOUR_HOST_ROOT_CA
-----END CERTIFICATE-----)PEM";
