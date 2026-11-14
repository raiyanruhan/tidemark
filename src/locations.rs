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
    (&["chittagong", "chattogram"], 22.33,  91.84,  "Chittagong, Bangladesh"),
    (&["sylhet"],                  24.90,  91.87,  "Sylhet, Bangladesh"),
    (&["rajshahi"],                24.37,  88.60,  "Rajshahi, Bangladesh"),
    (&["bogura", "bogra"],         24.85,  89.37,  "Bogura, Bangladesh"),
    (&["khulna"],                  22.82,  89.55,  "Khulna, Bangladesh"),
    (&["cairo"],                   30.06,  31.25,  "Cairo, Egypt"),
    (&["nairobi"],                 -1.29,  36.82,  "Nairobi, Kenya"),
    (&["lagos"],                    6.52,   3.38,  "Lagos, Nigeria"),
    (&["accra"],                    5.56,  -0.20,  "Accra, Ghana"),
    (&["addis ababa", "addis"],     9.03,  38.74,  "Addis Ababa, Ethiopia"),
    (&["dakar"],                   14.72, -17.47,  "Dakar, Senegal"),
    (&["mumbai"],                  19.08,  72.88,  "Mumbai, India"),
    (&["delhi", "new delhi"],      28.61,  77.21,  "Delhi, India"),
    (&["karachi"],                 24.86,  67.01,  "Karachi, Pakistan"),
    (&["islamabad"],               33.72,  73.04,  "Islamabad, Pakistan"),
    (&["kathmandu"],               27.72,  85.32,  "Kathmandu, Nepal"),
    (&["colombo"],                  6.93,  79.85,  "Colombo, Sri Lanka"),
    (&["bangkok"],                 13.75, 100.52,  "Bangkok, Thailand"),
    (&["jakarta"],                 -6.21, 106.85,  "Jakarta, Indonesia"),
    (&["manila"],                  14.60, 120.98,  "Manila, Philippines"),
    (&["hanoi"],                   21.03, 105.85,  "Hanoi, Vietnam"),
    (&["yangon"],                  16.87,  96.14,  "Yangon, Myanmar"),
    (&["beijing"],                 39.91, 116.39,  "Beijing, China"),
    (&["shanghai"],                31.23, 121.47,  "Shanghai, China"),
    (&["tokyo"],                   35.69, 139.69,  "Tokyo, Japan"),
    (&["seoul"],                   37.57, 126.98,  "Seoul, South Korea"),
    (&["dubai"],                   25.20,  55.27,  "Dubai, UAE"),
    (&["riyadh"],                  24.69,  46.72,  "Riyadh, Saudi Arabia"),
    (&["tehran"],                  35.69,  51.39,  "Tehran, Iran"),
    (&["istanbul"],                41.01,  28.95,  "Istanbul, Turkey"),
    (&["london"],                  51.51,  -0.13,  "London, UK"),
    (&["paris"],                   48.85,   2.35,  "Paris, France"),
    (&["berlin"],                  52.52,  13.40,  "Berlin, Germany"),
    (&["moscow"],                  55.75,  37.62,  "Moscow, Russia"),
    (&["new york", "newyork"],     40.71, -74.01,  "New York, USA"),
    (&["los angeles", "losangeles"], 34.05, -118.24, "Los Angeles, USA"),
    (&["miami"],                   25.77, -80.19,  "Miami, USA"),
    (&["mexico city", "mexico"],   19.43, -99.13,  "Mexico City, Mexico"),
    (&["bogota"],                   4.71, -74.07,  "Bogota, Colombia"),
    (&["lima"],                   -12.05, -77.04,  "Lima, Peru"),
    (&["sao paulo", "saopaulo"],  -23.55, -46.63,  "Sao Paulo, Brazil"),
    (&["buenos aires", "buenosaires"], -34.60, -58.38, "Buenos Aires, Argentina"),
    (&["sydney"],                 -33.87, 151.21,  "Sydney, Australia"),
];
