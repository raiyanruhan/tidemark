// (lat, lon, display_name). case-insensitive. None if not in table.
pub fn resolve_location(name: &str) -> Option<(f64, f64, String)> {
    let key = name.to_lowercase().replace(['-', '_'], " ");
    let entry = LOCATIONS.iter().find(|(aliases, _, _, _)| {
        aliases.iter().any(|a| *a == key.as_str())
    })?;
    Some((entry.1, entry.2, entry.3.to_string()))
}

// (aliases, lat, lon, display_name)
static LOCATIONS: &[(&[&str], f64, f64, &str)] = &[
    (&["dhaka"],                   23.81,  90.41,  "Dhaka, Bangladesh"),
    (&["chittagong", "chattogram"], 22.36,  91.80,  "Chittagong, Bangladesh"),
    (&["sylhet"],                  24.90,  91.87,  "Sylhet, Bangladesh"),
    (&["rajshahi"],                24.37,  88.60,  "Rajshahi, Bangladesh"),
    (&["khulna"],                  22.82,  89.55,  "Khulna, Bangladesh"),
    (&["cairo"],                   30.06,  31.25,  "Cairo, Egypt"),
    (&["nairobi"],                 -1.29,  36.82,  "Nairobi, Kenya"),
    (&["lagos"],                    6.52,   3.38,  "Lagos, Nigeria"),
    (&["mumbai"],                  19.08,  72.88,  "Mumbai, India"),
    (&["delhi", "new delhi"],      28.70,  77.10,  "Delhi, India"),
    (&["karachi"],                 24.86,  67.01,  "Karachi, Pakistan"),
    (&["jakarta"],                 -6.21, 106.85,  "Jakarta, Indonesia"),
    (&["manila"],                  14.60, 120.98,  "Manila, Philippines"),
    (&["bangkok"],                 13.75, 100.52,  "Bangkok, Thailand"),
    (&["addis ababa", "addis"],     9.03,  38.74,  "Addis Ababa, Ethiopia"),
    (&["dakar"],                   14.72, -17.47,  "Dakar, Senegal"),
    (&["lima"],                   -12.05, -77.04,  "Lima, Peru"),
    (&["bogota"],                   4.71, -74.07,  "Bogota, Colombia"),
    (&["new york"],                40.71, -74.01,  "New York, USA"),
    (&["london"],                  51.51,  -0.13,  "London, UK"),
    (&["tokyo"],                   35.69, 139.69,  "Tokyo, Japan"),
    (&["sydney"],                 -33.87, 151.21,  "Sydney, Australia"),
    (&["beijing"],                 39.91, 116.39,  "Beijing, China"),
    (&["riyadh"],                  24.69,  46.72,  "Riyadh, Saudi Arabia"),
    (&["islamabad"],               33.72,  73.04,  "Islamabad, Pakistan"),
];
