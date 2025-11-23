import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.database import SessionLocal
from models.models import (
    Organization, Song, SongStreamingMetrics, TerritoryRevenue, ValuationCalculation
)
from datetime import datetime, date, timedelta
import random

def seed_valuation_data():
    db = SessionLocal()
    
    try:
        org = db.query(Organization).first()
        if not org:
            print("No organization found. Please run init_gotcha_db.py first.")
            return
        
        songs = db.query(Song).filter(Song.organization_id == org.id).all()
        if not songs:
            print("No songs found. Please run init_gotcha_db.py first.")
            return
        
        print(f"Seeding valuation data for {len(songs)} songs in '{org.name}'...")
        
        existing_metrics = db.query(SongStreamingMetrics).count()
        if existing_metrics > 0:
            print(f"Deleting {existing_metrics} existing streaming metrics...")
            db.query(SongStreamingMetrics).delete()
        
        existing_territory = db.query(TerritoryRevenue).count()
        if existing_territory > 0:
            print(f"Deleting {existing_territory} existing territory revenues...")
            db.query(TerritoryRevenue).delete()
        
        existing_valuations = db.query(ValuationCalculation).count()
        if existing_valuations > 0:
            print(f"Deleting {existing_valuations} existing valuations...")
            db.query(ValuationCalculation).delete()
        
        db.commit()
        
        period_date = date.today() - timedelta(days=30)
        
        territories = [
            ("US", "United States"),
            ("UK", "United Kingdom"),
            ("CA", "Canada"),
            ("DE", "Germany"),
            ("FR", "France"),
            ("AU", "Australia"),
            ("JP", "Japan"),
            ("BR", "Brazil"),
            ("MX", "Mexico"),
            ("ES", "Spain")
        ]
        
        for song in songs:
            base_streams = random.randint(50000, 10000000)
            age_years = (date.today() - song.release_date).days / 365 if song.release_date else 1
            age_multiplier = max(0.3, 1.5 - (age_years * 0.15))
            total_streams = int(base_streams * age_multiplier)
            
            ad_supported = int(total_streams * random.uniform(0.15, 0.35))
            premium = total_streams - ad_supported
            on_demand = int(total_streams * random.uniform(0.85, 0.95))
            programmed = total_streams - on_demand
            audio = int(total_streams * random.uniform(0.92, 0.99))
            video = total_streams - audio
            song_sales = random.randint(0, 500)
            
            ownership = random.choice([1.0, 0.5, 0.25, 0.333, 0.125])
            
            metrics = SongStreamingMetrics(
                song_id=song.id,
                organization_id=org.id,
                period_date=period_date,
                total_streams=total_streams,
                ad_supported_streams=ad_supported,
                premium_streams=premium,
                interactive_streams=int(total_streams * 0.95),
                on_demand_streams=on_demand,
                programmed_streams=programmed,
                audio_streams=audio,
                video_streams=video,
                song_sales=song_sales,
                ownership_percentage=ownership
            )
            db.add(metrics)
            
            us_pct = random.uniform(0.40, 0.65)
            territory_distribution = {
                "US": us_pct,
                "UK": random.uniform(0.08, 0.15),
                "CA": random.uniform(0.04, 0.08),
                "DE": random.uniform(0.03, 0.07),
                "FR": random.uniform(0.02, 0.05),
                "AU": random.uniform(0.02, 0.04),
                "JP": random.uniform(0.01, 0.03),
                "BR": random.uniform(0.01, 0.03),
                "MX": random.uniform(0.01, 0.02),
                "ES": random.uniform(0.01, 0.02)
            }
            
            total_pct = sum(territory_distribution.values())
            territory_distribution = {k: v/total_pct for k, v in territory_distribution.items()}
            
            for territory_code, territory_name in territories:
                pct = territory_distribution[territory_code]
                terr_streams = int(total_streams * pct)
                
                ICARUS_STREAM_RATE = 0.0012
                gross_revenue = terr_streams * ICARUS_STREAM_RATE
                
                publishing_split = random.uniform(0.55, 0.65)
                publishing_revenue_cents = int(gross_revenue * publishing_split * ownership)
                master_revenue_cents = int(gross_revenue * (1 - publishing_split) * ownership)
                
                territory = TerritoryRevenue(
                    song_id=song.id,
                    organization_id=org.id,
                    period_date=period_date,
                    territory_code=territory_code,
                    territory_name=territory_name,
                    total_streams=terr_streams,
                    publishing_revenue_cents=publishing_revenue_cents,
                    master_revenue_cents=master_revenue_cents,
                    total_revenue_cents=publishing_revenue_cents + master_revenue_cents
                )
                db.add(territory)
            
            ICARUS_STREAM_RATE = 0.0012
            monthly_revenue_cents = int(total_streams * ICARUS_STREAM_RATE * ownership * 100)
            annual_revenue_cents = monthly_revenue_cents * 12
            thirty_day_revenue_cents = monthly_revenue_cents
            ninety_day_revenue_cents = monthly_revenue_cents * 3
            
            streaming_multiple = random.uniform(18, 28)
            streaming_multiple_value_cents = int(annual_revenue_cents * streaming_multiple)
            
            revenue_multiple = random.uniform(8, 15)
            revenue_multiple_value_cents = int(annual_revenue_cents * revenue_multiple)
            
            market_comp_base = (streaming_multiple_value_cents + revenue_multiple_value_cents) / 2
            market_variance = random.uniform(0.85, 1.15)
            market_comp_value_cents = int(market_comp_base * market_variance)
            
            health_bonus = song.status_health_score / 100 if song.status_health_score else 0.5
            recency_bonus = max(0.8, min(1.2, 2 - age_years * 0.1))
            growth_rate = random.uniform(-0.05, 0.35)
            
            black_box_multiplier = (
                0.3 * health_bonus +
                0.25 * recency_bonus +
                0.25 * (1 + growth_rate) +
                0.2
            )
            black_box_value_cents = int(annual_revenue_cents * black_box_multiplier * 12)
            
            final_valuation_cents = int(
                streaming_multiple_value_cents * 0.25 +
                revenue_multiple_value_cents * 0.25 +
                market_comp_value_cents * 0.25 +
                black_box_value_cents * 0.25
            )
            
            risk_score = random.uniform(0.3, 0.7)
            
            valuation = ValuationCalculation(
                song_id=song.id,
                organization_id=org.id,
                calculation_date=datetime.utcnow(),
                streaming_multiple_value_cents=streaming_multiple_value_cents,
                revenue_multiple_value_cents=revenue_multiple_value_cents,
                market_comp_value_cents=market_comp_value_cents,
                black_box_value_cents=black_box_value_cents,
                final_valuation_cents=final_valuation_cents,
                valuation_methodology="HYBRID",
                thirty_day_revenue_cents=thirty_day_revenue_cents,
                ninety_day_revenue_cents=ninety_day_revenue_cents,
                annual_revenue_cents=annual_revenue_cents,
                growth_rate=growth_rate,
                risk_score=risk_score,
                calc_metadata={
                    "streaming_multiple": streaming_multiple,
                    "revenue_multiple": revenue_multiple,
                    "health_bonus": health_bonus,
                    "recency_bonus": recency_bonus,
                    "stream_rate": stream_rate,
                    "ownership_percentage": ownership
                }
            )
            db.add(valuation)
        
        db.commit()
        
        total_metrics = db.query(SongStreamingMetrics).count()
        total_territory = db.query(TerritoryRevenue).count()
        total_valuations = db.query(ValuationCalculation).count()
        
        total_value = db.query(ValuationCalculation).filter(
            ValuationCalculation.organization_id == org.id
        ).all()
        catalog_value = sum(v.final_valuation_cents for v in total_value) / 100
        annual_revenue = sum(v.annual_revenue_cents for v in total_value) / 100
        
        print(f"\n✓ Valuation data seeded successfully!")
        print(f"  - {total_metrics} streaming metrics records")
        print(f"  - {total_territory} territory revenue records")
        print(f"  - {total_valuations} valuation calculations")
        print(f"\n📊 Catalog Summary:")
        print(f"  - Total Catalog Value: ${catalog_value:,.2f}")
        print(f"  - Annual Revenue: ${annual_revenue:,.2f}")
        
    except Exception as e:
        print(f"Error seeding valuation data: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_valuation_data()
