"""
Streaming Platform Rates Configuration (2024-2025)

Publishing mechanical rates are consistent across platforms (~$0.0012/stream).
Master recording rates vary significantly by platform and tier.

Data sources: Digital Music News, MIDiA Research Q4 2024, Streaming Calculator 2025
Last updated: January 2025
"""

# Publishing mechanical rates (consistent across platforms)
PUBLISHING_RATE_PREMIUM = 0.0012
PUBLISHING_RATE_AD_SUPPORTED = 0.0004

# Master recording rates by platform (2024-2025 data)
MASTER_RATES = {
    'spotify': {
        'premium': 0.004,
        'ad_supported': 0.001,
        'description': 'Spotify requires 1,000 annual streams minimum since April 2024'
    },
    'apple_music': {
        'premium': 0.010,
        'ad_supported': 0.010,
        'description': 'Apple Music is premium-only, no free tier'
    },
    'youtube_music': {
        'premium': 0.008,
        'ad_supported': 0.002,
        'description': 'Wide variance; premium streams cluster at top of range'
    },
    'amazon_music': {
        'premium': 0.004,
        'ad_supported': 0.0015,
        'description': 'Rates vary by tier (Prime, Unlimited, ad-supported)'
    },
    'tidal': {
        'premium': 0.01284,
        'ad_supported': 0.01284,
        'description': 'Highest payout rate; premium-only HiFi service'
    }
}

# Global market share (2024 data)
MARKET_SHARE = {
    'spotify': 0.34,
    'apple_music': 0.125,
    'youtube_music': 0.085,
    'amazon_music': 0.095,
    'tidal': 0.005,
    'tencent_music': 0.145,
    'others': 0.205
}

# Platforms we track (exclude China-focused Tencent)
TRACKED_PLATFORMS = ['spotify', 'apple_music', 'youtube_music', 'amazon_music', 'tidal']

# Combined market share of tracked platforms
TRACKED_MARKET_SHARE = sum(MARKET_SHARE[platform] for platform in TRACKED_PLATFORMS)

# Market share multiplier for estimating total market from tracked platforms
# If we know 62.5% of market, multiply by 1.6 to estimate 100%
MARKET_MULTIPLIER = 1.0 / TRACKED_MARKET_SHARE

def get_publishing_rate(stream_type='premium'):
    """Get publishing mechanical rate per stream"""
    if stream_type == 'ad_supported':
        return PUBLISHING_RATE_AD_SUPPORTED
    return PUBLISHING_RATE_PREMIUM

def get_master_rate(platform, stream_type='premium'):
    """Get master recording rate per stream for a platform"""
    if platform not in MASTER_RATES:
        return MASTER_RATES['spotify'][stream_type]
    
    if stream_type not in MASTER_RATES[platform]:
        return MASTER_RATES[platform]['premium']
    
    return MASTER_RATES[platform][stream_type]

def calculate_platform_revenue(streams, platform, stream_type, ownership_pct):
    """Calculate revenue for a specific platform"""
    master_rate = get_master_rate(platform, stream_type)
    publishing_rate = get_publishing_rate(stream_type)
    
    master_revenue = streams * master_rate * (ownership_pct / 100.0)
    publishing_revenue = streams * publishing_rate * (ownership_pct / 100.0)
    
    return {
        'publishing': publishing_revenue,
        'master': master_revenue,
        'total': publishing_revenue + master_revenue
    }
