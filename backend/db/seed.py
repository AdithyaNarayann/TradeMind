"""
Database seeding script for development/testing.
Populates DB with dummy data.
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import bcrypt
from dotenv import load_dotenv

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Load environment variables
load_dotenv(backend_dir / ".env")

from db.database.base import Base
from db.models import (
    User,
    ApiKey,
    NegotiationSession,
    NegotiationMode,
    SessionStatus,
    NegotiationTurn,
    TurnDecision,
    SessionAnalytics,
    MarketPriceSnapshot,
)

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@127.0.0.1:5432/negotiation_bot")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def seed_database():
    """Seed the database with dummy data."""
    
    # Create engine and session
    engine = create_engine(DATABASE_URL, echo=True)
    
    # Create all tables
    print("Creating tables...")
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("\nSeeding data...")
        
        # 1. Create Users (Sellers)
        user1 = User(
            email="seller1@example.com",
            hashed_password=hash_password("password123"),
            is_active=True,
        )
        
        user2 = User(
            email="seller2@example.com",
            hashed_password=hash_password("password456"),
            is_active=True,
        )
        
        session.add_all([user1, user2])
        session.flush()  # Get IDs
        
        print(f"[OK] Created user: {user1.email}")
        print(f"[OK] Created user: {user2.email}")
        
        # 2. Create API Keys
        api_key1 = ApiKey(
            user_id=user1.id,
            api_key=hash_password("sk_test_abc123"),
            is_active=True,
        )
        
        api_key2 = ApiKey(
            user_id=user2.id,
            api_key=hash_password("sk_test_xyz789"),
            is_active=True,
            last_used_at=datetime.utcnow() - timedelta(hours=2),
        )
        
        session.add_all([api_key1, api_key2])
        print("[OK] Created API keys")
        
        # 3. Create Market Price Snapshots
        market1 = MarketPriceSnapshot(
            product_id="PROD-001",
            market_avg_price=Decimal("150.00"),
            lowest_price=Decimal("120.00"),
            highest_price=Decimal("180.00"),
            competitor_count=5,
            competition_density=Decimal("0.75"),
        )
        
        market2 = MarketPriceSnapshot(
            product_id="PROD-002",
            market_avg_price=Decimal("89.99"),
            lowest_price=Decimal("75.00"),
            highest_price=Decimal("110.00"),
            competitor_count=8,
            competition_density=Decimal("0.85"),
        )
        
        session.add_all([market1, market2])
        print("[OK] Created market snapshots")
        
        # 4. Create Negotiation Sessions
        session1 = NegotiationSession(
            user_id=user1.id,
            mode=NegotiationMode.MAX_PROFIT,
            status=SessionStatus.ACCEPTED,
            product_id="PROD-001",
            product_name="Premium Widget A",
            product_sku="WGT-A-001",
            product_category="Electronics",
            urgency="high",
            inventory_pressure="low_stock",
            relationship_priority="new_customer",
            max_rounds=5,
            rounds_taken=3,
            initial_offer_price=Decimal("180.00"),
            final_price=Decimal("155.00"),
            created_at=datetime.utcnow() - timedelta(days=2),
            updated_at=datetime.utcnow() - timedelta(days=2),
            closed_at=datetime.utcnow() - timedelta(days=2),
        )
        
        session2 = NegotiationSession(
            user_id=user1.id,
            mode=NegotiationMode.MIN_LOSS,
            status=SessionStatus.ACTIVE,
            product_id="PROD-002",
            product_name="Standard Widget B",
            product_sku="WGT-B-002",
            product_category="Electronics",
            urgency="normal",
            inventory_pressure="normal",
            relationship_priority="repeat_customer",
            max_rounds=10,
            rounds_taken=2,
            initial_offer_price=Decimal("110.00"),
            final_price=None,
            created_at=datetime.utcnow() - timedelta(hours=3),
            updated_at=datetime.utcnow() - timedelta(minutes=15),
            closed_at=None,
        )
        
        session3 = NegotiationSession(
            user_id=user2.id,
            mode=NegotiationMode.MAX_PROFIT,
            status=SessionStatus.REJECTED,
            product_id="PROD-003",
            product_name="Deluxe Widget C",
            product_sku="WGT-C-003",
            product_category="Home & Garden",
            urgency="low",
            inventory_pressure="high_stock",
            relationship_priority="vip_customer",
            max_rounds=8,
            rounds_taken=5,
            initial_offer_price=Decimal("200.00"),
            final_price=None,
            created_at=datetime.utcnow() - timedelta(days=1),
            updated_at=datetime.utcnow() - timedelta(days=1),
            closed_at=datetime.utcnow() - timedelta(days=1),
        )
        
        session.add_all([session1, session2, session3])
        session.flush()  # Get IDs
        
        print(f"[OK] Created session: {session1.product_name} ({session1.status.value})")
        print(f"[OK] Created session: {session2.product_name} ({session2.status.value})")
        print(f"[OK] Created session: {session3.product_name} ({session3.status.value})")
        
        # 5. Create Negotiation Turns for Session 1 (Completed)
        turn1_1 = NegotiationTurn(
            session_id=session1.id,
            round_number=1,
            buyer_offered_price=Decimal("140.00"),
            buyer_offered_quantity=10,
            buyer_message="Looking for bulk discount",
            decision=TurnDecision.COUNTER,
            counter_offer_price=Decimal("170.00"),
            accepted_price=None,
            concession_made=Decimal("10.00"),
            remaining_concession_budget=Decimal("20.00"),
            margin_percentage=Decimal("0.25"),
            profit_per_unit=Decimal("45.00"),
            total_profit=Decimal("450.00"),
            within_constraints=True,
            constraint_violations=None,
            created_at=datetime.utcnow() - timedelta(days=2, hours=3),
        )
        
        turn1_2 = NegotiationTurn(
            session_id=session1.id,
            round_number=2,
            buyer_offered_price=Decimal("150.00"),
            buyer_offered_quantity=10,
            buyer_message="Can you meet halfway?",
            decision=TurnDecision.COUNTER,
            counter_offer_price=Decimal("160.00"),
            accepted_price=None,
            concession_made=Decimal("10.00"),
            remaining_concession_budget=Decimal("10.00"),
            margin_percentage=Decimal("0.22"),
            profit_per_unit=Decimal("37.00"),
            total_profit=Decimal("370.00"),
            within_constraints=True,
            constraint_violations=None,
            created_at=datetime.utcnow() - timedelta(days=2, hours=2),
        )
        
        turn1_3 = NegotiationTurn(
            session_id=session1.id,
            round_number=3,
            buyer_offered_price=Decimal("155.00"),
            buyer_offered_quantity=10,
            buyer_message="Final offer",
            decision=TurnDecision.ACCEPT,
            counter_offer_price=None,
            accepted_price=Decimal("155.00"),
            concession_made=Decimal("5.00"),
            remaining_concession_budget=Decimal("5.00"),
            margin_percentage=Decimal("0.20"),
            profit_per_unit=Decimal("32.00"),
            total_profit=Decimal("320.00"),
            within_constraints=True,
            constraint_violations=None,
            created_at=datetime.utcnow() - timedelta(days=2, hours=1),
        )
        
        # 6. Create Turns for Session 2 (Active)
        turn2_1 = NegotiationTurn(
            session_id=session2.id,
            round_number=1,
            buyer_offered_price=Decimal("80.00"),
            buyer_offered_quantity=5,
            buyer_message="Need lower price",
            decision=TurnDecision.COUNTER,
            counter_offer_price=Decimal("100.00"),
            accepted_price=None,
            concession_made=Decimal("10.00"),
            remaining_concession_budget=Decimal("15.00"),
            margin_percentage=Decimal("0.18"),
            profit_per_unit=Decimal("18.00"),
            total_profit=Decimal("90.00"),
            within_constraints=True,
            constraint_violations=None,
            created_at=datetime.utcnow() - timedelta(hours=3),
        )
        
        turn2_2 = NegotiationTurn(
            session_id=session2.id,
            round_number=2,
            buyer_offered_price=Decimal("90.00"),
            buyer_offered_quantity=5,
            buyer_message="Better, but still high",
            decision=TurnDecision.COUNTER,
            counter_offer_price=Decimal("95.00"),
            accepted_price=None,
            concession_made=Decimal("5.00"),
            remaining_concession_budget=Decimal("10.00"),
            margin_percentage=Decimal("0.15"),
            profit_per_unit=Decimal("13.00"),
            total_profit=Decimal("65.00"),
            within_constraints=True,
            constraint_violations=None,
            created_at=datetime.utcnow() - timedelta(minutes=15),
        )
        
        # 7. Create Turns for Session 3 (Rejected)
        turn3_1 = NegotiationTurn(
            session_id=session3.id,
            round_number=1,
            buyer_offered_price=Decimal("100.00"),
            buyer_offered_quantity=20,
            buyer_message="Very low budget",
            decision=TurnDecision.REJECT,
            counter_offer_price=None,
            accepted_price=None,
            concession_made=Decimal("0.00"),
            remaining_concession_budget=Decimal("30.00"),
            margin_percentage=None,
            profit_per_unit=None,
            total_profit=None,
            within_constraints=False,
            constraint_violations=["price_below_minimum", "unacceptable_margin"],
            created_at=datetime.utcnow() - timedelta(days=1),
        )
        
        session.add_all([turn1_1, turn1_2, turn1_3, turn2_1, turn2_2, turn3_1])
        print("[OK] Created negotiation turns")
        
        # 8. Create Session Analytics
        analytics1 = SessionAnalytics(
            session_id=session1.id,
            buyer_first_offer=Decimal("140.00"),
            total_concession_given=Decimal("25.00"),
            concession_percentage=Decimal("13.89"),
            rounds_used=3,
            rounds_available=5,
            efficiency_score=Decimal("0.85"),
            gross_profit=Decimal("320.00"),
            profit_margin=Decimal("20.65"),
            constraint_violations_attempted=0,
            walk_away_triggered=False,
            violations_detail=None,
        )
        
        analytics2 = SessionAnalytics(
            session_id=session2.id,
            buyer_first_offer=Decimal("80.00"),
            total_concession_given=Decimal("15.00"),
            concession_percentage=Decimal("13.64"),
            rounds_used=2,
            rounds_available=10,
            efficiency_score=Decimal("0.78"),
            gross_profit=Decimal("65.00"),
            profit_margin=Decimal("13.68"),
            constraint_violations_attempted=0,
            walk_away_triggered=False,
            violations_detail=None,
        )
        
        analytics3 = SessionAnalytics(
            session_id=session3.id,
            buyer_first_offer=Decimal("100.00"),
            total_concession_given=Decimal("0.00"),
            concession_percentage=Decimal("0.00"),
            rounds_used=1,
            rounds_available=8,
            efficiency_score=Decimal("0.00"),
            gross_profit=None,
            profit_margin=None,
            constraint_violations_attempted=2,
            walk_away_triggered=True,
            violations_detail=["price_below_minimum", "unacceptable_margin"],
        )
        
        session.add_all([analytics1, analytics2, analytics3])
        print("[OK] Created analytics")
        
        # Commit all changes
        session.commit()
        print("\n[SUCCESS] Database seeded successfully!")
        
        # Print summary
        print("\n" + "="*50)
        print("SUMMARY")
        print("="*50)
        print(f"Users: 2")
        print(f"API Keys: 2")
        print(f"Sessions: 3 (1 accepted, 1 active, 1 rejected)")
        print(f"Turns: 6")
        print(f"Analytics: 3")
        print(f"Market Snapshots: 2")
        print("="*50)
        
    except Exception as e:
        session.rollback()
        print(f"\n[ERROR] Error seeding database: {e}")
        raise
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    seed_database()
