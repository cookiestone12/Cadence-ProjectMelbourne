import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Base, engine, get_db
from models.models import (
    User, Organization, OrganizationMember, Creator, Song, SongCredit,
    SongDSPLink, ChecklistItem, SongChecklistStatus, SongValuationSnapshot
)
from passlib.context import CryptContext
from datetime import datetime, date, timedelta
import random

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def init_database():
    print("Initializing Gotcha Catalog Manager database...")
    
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    
    db = next(get_db())
    
    try:
        print("Creating checklist items...")
        checklist_items = [
            ChecklistItem(code="AD-01", category="ADMIN", description="Contract sent to placement partner", weight=10),
            ChecklistItem(code="AD-02", category="ADMIN", description="Contract executed/signed", weight=15),
            ChecklistItem(code="AD-03", category="ADMIN", description="Invoice submitted", weight=10),
            ChecklistItem(code="LG-01", category="LEGAL", description="Rights clearance completed", weight=15),
            ChecklistItem(code="LG-02", category="LEGAL", description="Publishing splits confirmed", weight=10),
            ChecklistItem(code="MD-01", category="METADATA", description="ISRC assigned", weight=5),
            ChecklistItem(code="MD-02", category="METADATA", description="ISWC assigned", weight=5),
            ChecklistItem(code="MD-03", category="METADATA", description="Credits finalized", weight=5),
            ChecklistItem(code="DSP-01", category="DSP", description="Registered with DSPs", weight=10),
            ChecklistItem(code="DSP-02", category="DSP", description="Apple Music link verified", weight=5),
            ChecklistItem(code="DSP-03", category="DSP", description="Spotify link verified", weight=5),
            ChecklistItem(code="SY-01", category="SYNC", description="Registered with PRO", weight=10),
            ChecklistItem(code="SY-02", category="SYNC", description="Publisher notified", weight=5),
            ChecklistItem(code="PY-01", category="PAYMENT", description="Payment received", weight=20),
        ]
        db.add_all(checklist_items)
        db.flush()
        
        print("Creating Demo Label Co. organization...")
        org = Organization(
            name="Demo Label Co.",
            type="LABEL"
        )
        db.add(org)
        db.flush()
        
        print("Creating admin user...")
        admin_user = User(
            username="admin",
            email="admin@demolabel.com",
            hashed_password=get_password_hash("demo123"),
            is_admin=True
        )
        db.add(admin_user)
        db.flush()
        
        print("Adding admin to organization...")
        org_member = OrganizationMember(
            organization_id=org.id,
            user_id=admin_user.id,
            role="OWNER"
        )
        db.add(org_member)
        db.flush()
        
        print("Creating 6 creators (roster)...")
        creators_data = [
            {
                "display_name": "Maya Rivers",
                "legal_name": "Maya Elena Rivers",
                "roles": ["ARTIST", "SONGWRITER"],
                "primary_territory": "US",
                "primary_pro": "ASCAP",
                "primary_ipi": "00123456789",
                "hero_image_url": None
            },
            {
                "display_name": "Jordan Blake",
                "legal_name": "Jordan Michael Blake",
                "roles": ["SONGWRITER", "PRODUCER"],
                "primary_territory": "US",
                "primary_pro": "BMI",
                "primary_ipi": "00234567890",
                "hero_image_url": None
            },
            {
                "display_name": "Alex Chen",
                "legal_name": "Alexander Chen",
                "roles": ["PRODUCER"],
                "primary_territory": "US",
                "primary_pro": "ASCAP",
                "primary_ipi": "00345678901",
                "hero_image_url": None
            },
            {
                "display_name": "Sophia Martinez",
                "legal_name": "Sophia Grace Martinez",
                "roles": ["SONGWRITER"],
                "primary_territory": "US",
                "primary_pro": "SESAC",
                "primary_ipi": "00456789012",
                "hero_image_url": None
            },
            {
                "display_name": "The Neon Collective",
                "legal_name": None,
                "roles": ["ARTIST"],
                "primary_territory": "UK",
                "primary_pro": "PRS",
                "primary_ipi": "00567890123",
                "hero_image_url": None
            },
            {
                "display_name": "Marcus Young",
                "legal_name": "Marcus Anthony Young",
                "roles": ["SONGWRITER", "PRODUCER"],
                "primary_territory": "US",
                "primary_pro": "BMI",
                "primary_ipi": "00678901234",
                "hero_image_url": None
            }
        ]
        
        creators = []
        for creator_data in creators_data:
            creator = Creator(
                organization_id=org.id,
                **creator_data
            )
            db.add(creator)
            creators.append(creator)
        db.flush()
        
        print("Creating 35 songs with credits, DSP links, and checklist statuses...")
        
        songs_data = [
            {"title": "Midnight Dreams", "primary_artist": "Maya Rivers", "project_title": "Dreamscape", "release_date": date(2024, 3, 15), "isrc": "USRC12400001", "iswc": "T-123.456.789-1"},
            {"title": "Electric Heart", "primary_artist": "The Neon Collective", "project_title": "Neon Nights", "release_date": date(2024, 5, 20), "isrc": "GBRC12400002", "iswc": "T-123.456.789-2"},
            {"title": "Shadows in the Rain", "primary_artist": "Maya Rivers", "project_title": "Dreamscape", "release_date": date(2024, 3, 15), "isrc": "USRC12400003", "iswc": "T-123.456.789-3"},
            {"title": "Lost Highway", "primary_artist": "The Neon Collective", "project_title": "Neon Nights", "release_date": date(2024, 5, 20), "isrc": "GBRC12400004", "iswc": "T-123.456.789-4"},
            {"title": "Golden Hour", "primary_artist": "Maya Rivers", "project_title": None, "release_date": date(2024, 8, 10), "isrc": "USRC12400005", "iswc": "T-123.456.789-5"},
            {"title": "Break the Silence", "primary_artist": "The Neon Collective", "project_title": "Neon Nights", "release_date": date(2024, 5, 20), "isrc": "GBRC12400006", "iswc": "T-123.456.789-6"},
            {"title": "Wildfire", "primary_artist": "Maya Rivers feat. The Neon Collective", "project_title": None, "release_date": date(2024, 9, 5), "isrc": "USRC12400007", "iswc": "T-123.456.789-7"},
            {"title": "Echoes of Tomorrow", "primary_artist": "The Neon Collective", "project_title": "Future Past", "release_date": date(2024, 11, 1), "isrc": "GBRC12400008", "iswc": "T-123.456.789-8"},
            {"title": "Gravity", "primary_artist": "Maya Rivers", "project_title": "Dreamscape", "release_date": date(2024, 3, 15), "isrc": "USRC12400009", "iswc": "T-123.456.789-9"},
            {"title": "Neon Paradise", "primary_artist": "The Neon Collective", "project_title": "Neon Nights", "release_date": date(2024, 5, 20), "isrc": "GBRC12400010", "iswc": "T-123.456.789-10"},
            {"title": "Burning Bridges", "primary_artist": "Maya Rivers", "project_title": None, "release_date": date(2024, 10, 12), "isrc": "USRC12400011", "iswc": "T-123.456.789-11"},
            {"title": "Crystal Clear", "primary_artist": "The Neon Collective", "project_title": "Future Past", "release_date": date(2024, 11, 1), "isrc": "GBRC12400012", "iswc": "T-123.456.789-12"},
            {"title": "Waves", "primary_artist": "Maya Rivers", "project_title": None, "release_date": date(2024, 7, 22), "isrc": "USRC12400013", "iswc": "T-123.456.789-13"},
            {"title": "Starlight Symphony", "primary_artist": "The Neon Collective", "project_title": "Future Past", "release_date": date(2024, 11, 1), "isrc": "GBRC12400014", "iswc": "T-123.456.789-14"},
            {"title": "Fading Memories", "primary_artist": "Maya Rivers", "project_title": "Dreamscape", "release_date": date(2024, 3, 15), "isrc": "USRC12400015", "iswc": "T-123.456.789-15"},
            {"title": "Thunder Road", "primary_artist": "The Neon Collective", "project_title": "Neon Nights", "release_date": date(2024, 5, 20), "isrc": "GBRC12400016", "iswc": "T-123.456.789-16"},
            {"title": "Silent Storm", "primary_artist": "Maya Rivers", "project_title": None, "release_date": date(2024, 6, 30), "isrc": "USRC12400017", "iswc": "T-123.456.789-17"},
            {"title": "Velvet Skies", "primary_artist": "The Neon Collective", "project_title": "Future Past", "release_date": date(2024, 11, 1), "isrc": "GBRC12400018", "iswc": "T-123.456.789-18"},
            {"title": "Phoenix Rising", "primary_artist": "Maya Rivers", "project_title": None, "release_date": date(2024, 11, 15), "isrc": "USRC12400019", "iswc": "T-123.456.789-19"},
            {"title": "Digital Dreams", "primary_artist": "The Neon Collective", "project_title": "Neon Nights", "release_date": date(2024, 5, 20), "isrc": "GBRC12400020", "iswc": "T-123.456.789-20"},
            {"title": "Cosmic Love", "primary_artist": "Maya Rivers", "project_title": "Dreamscape", "release_date": date(2024, 3, 15), "isrc": "USRC12400021", "iswc": "T-123.456.789-21"},
            {"title": "Neon Lights", "primary_artist": "The Neon Collective", "project_title": "Neon Nights", "release_date": date(2024, 5, 20), "isrc": "GBRC12400022", "iswc": "T-123.456.789-22"},
            {"title": "Broken Wings", "primary_artist": "Maya Rivers", "project_title": None, "release_date": date(2024, 8, 25), "isrc": "USRC12400023", "iswc": "T-123.456.789-23"},
            {"title": "Quantum Leap", "primary_artist": "The Neon Collective", "project_title": "Future Past", "release_date": date(2024, 11, 1), "isrc": "GBRC12400024", "iswc": "T-123.456.789-24"},
            {"title": "Into the Abyss", "primary_artist": "Maya Rivers", "project_title": None, "release_date": date(2024, 9, 18), "isrc": "USRC12400025", "iswc": "T-123.456.789-25"},
            {"title": "Pulse of the City", "primary_artist": "The Neon Collective", "project_title": "Neon Nights", "release_date": date(2024, 5, 20), "isrc": "GBRC12400026", "iswc": "T-123.456.789-26"},
            {"title": "Serenity", "primary_artist": "Maya Rivers", "project_title": "Dreamscape", "release_date": date(2024, 3, 15), "isrc": "USRC12400027", "iswc": "T-123.456.789-27"},
            {"title": "Neon Horizon", "primary_artist": "The Neon Collective", "project_title": "Future Past", "release_date": date(2024, 11, 1), "isrc": "GBRC12400028", "iswc": "T-123.456.789-28"},
            {"title": "Summer Nights", "primary_artist": "Maya Rivers", "project_title": None, "release_date": date(2024, 6, 15), "isrc": "USRC12400029", "iswc": "T-123.456.789-29"},
            {"title": "Electric Avenue", "primary_artist": "The Neon Collective", "project_title": "Neon Nights", "release_date": date(2024, 5, 20), "isrc": "GBRC12400030", "iswc": "T-123.456.789-30"},
            {"title": "Moonlight Serenade", "primary_artist": "Maya Rivers", "project_title": "Dreamscape", "release_date": date(2024, 3, 15), "isrc": "USRC12400031", "iswc": "T-123.456.789-31"},
            {"title": "Cyber Dreams", "primary_artist": "The Neon Collective", "project_title": "Future Past", "release_date": date(2024, 11, 1), "isrc": "GBRC12400032", "iswc": "T-123.456.789-32"},
            {"title": "Last Dance", "primary_artist": "Maya Rivers", "project_title": None, "release_date": date(2024, 10, 28), "isrc": "USRC12400033", "iswc": "T-123.456.789-33"},
            {"title": "Infinite Loop", "primary_artist": "The Neon Collective", "project_title": "Future Past", "release_date": date(2024, 11, 1), "isrc": "GBRC12400034", "iswc": "T-123.456.789-34"},
            {"title": "Whispers in the Wind", "primary_artist": "Maya Rivers", "project_title": None, "release_date": date(2024, 7, 8), "isrc": "USRC12400035", "iswc": "T-123.456.789-35"},
        ]
        
        songs = []
        for song_data in songs_data:
            health_score = random.randint(40, 100)
            
            has_contract_sent = health_score > 30
            has_contract_executed = health_score > 50
            is_registered_with_pro = health_score > 60
            is_registered_with_dsp = health_score > 60
            is_invoiced = health_score > 70
            is_paid = health_score > 85
            
            song = Song(
                organization_id=org.id,
                **song_data,
                status_health_score=health_score,
                has_contract_sent=has_contract_sent,
                has_contract_executed=has_contract_executed,
                is_registered_with_pro=is_registered_with_pro,
                is_registered_with_dsp=is_registered_with_dsp,
                is_invoiced=is_invoiced,
                is_paid=is_paid
            )
            db.add(song)
            songs.append(song)
        
        db.flush()
        
        print("Adding song credits...")
        for i, song in enumerate(songs):
            if "Maya Rivers" in song.primary_artist:
                db.add(SongCredit(song_id=song.id, creator_id=creators[0].id, role="ARTIST", share_percentage=100.0))
                db.add(SongCredit(song_id=song.id, creator_id=creators[0].id, role="SONGWRITER", share_percentage=50.0))
                db.add(SongCredit(song_id=song.id, creator_id=creators[1].id, role="SONGWRITER", share_percentage=50.0))
                db.add(SongCredit(song_id=song.id, creator_id=creators[2].id, role="PRODUCER", share_percentage=100.0))
                
                if "feat." in song.primary_artist:
                    db.add(SongCredit(song_id=song.id, creator_id=creators[4].id, role="FEATURED_ARTIST", share_percentage=None))
            
            elif "The Neon Collective" in song.primary_artist:
                db.add(SongCredit(song_id=song.id, creator_id=creators[4].id, role="ARTIST", share_percentage=100.0))
                db.add(SongCredit(song_id=song.id, creator_id=creators[3].id, role="SONGWRITER", share_percentage=40.0))
                db.add(SongCredit(song_id=song.id, creator_id=creators[5].id, role="SONGWRITER", share_percentage=60.0))
                db.add(SongCredit(song_id=song.id, creator_id=creators[5].id, role="PRODUCER", share_percentage=100.0))
        
        db.flush()
        
        print("Adding DSP links...")
        for song in songs:
            if random.random() > 0.2:
                db.add(SongDSPLink(
                    song_id=song.id,
                    platform="APPLE_MUSIC",
                    url=f"https://music.apple.com/us/album/{song.title.lower().replace(' ', '-')}/{song.id}"
                ))
            
            if random.random() > 0.3:
                db.add(SongDSPLink(
                    song_id=song.id,
                    platform="SPOTIFY",
                    url=f"https://open.spotify.com/track/{song.id}xyz"
                ))
        
        db.flush()
        
        print("Adding checklist statuses...")
        for song in songs:
            for item in checklist_items:
                if song.status_health_score >= 90:
                    status = "COMPLETED"
                elif song.status_health_score >= 70:
                    status = random.choice(["COMPLETED", "IN_PROGRESS", "IN_PROGRESS"])
                elif song.status_health_score >= 50:
                    status = random.choice(["IN_PROGRESS", "NOT_STARTED", "NOT_STARTED"])
                else:
                    status = random.choice(["NOT_STARTED", "BLOCKED"])
                
                db.add(SongChecklistStatus(
                    song_id=song.id,
                    checklist_item_id=item.id,
                    status=status
                ))
        
        db.flush()
        
        print("Adding sample valuations...")
        for i, song in enumerate(songs[:10]):
            if random.random() > 0.5:
                db.add(SongValuationSnapshot(
                    song_id=song.id,
                    valuation_cents=random.randint(50000, 500000),
                    source="MANUAL",
                    notes="Demo valuation snapshot"
                ))
        
        db.commit()
        print("✓ Database initialization completed successfully!")
        print("\nDemo Credentials:")
        print("  Username: admin")
        print("  Email: admin@demolabel.com")
        print("  Password: demo123")
        print("\nOrganization: Demo Label Co.")
        print(f"Creators: {len(creators)}")
        print(f"Songs: {len(songs)}")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
