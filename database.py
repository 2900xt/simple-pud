from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

class Player(Base):
    __tablename__ = 'players'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    hands_played = Column(Integer, default=0)
    vpip_count = Column(Integer, default=0) # Voluntarily Put Money In Pot
    pfr_count = Column(Integer, default=0)  # Pre-Flop Raise
    three_bet_count = Column(Integer, default=0)
    aggression_factor = Column(Float, default=0.0)
    notes = Column(String, default="")

    def to_dict(self):
        return {
            'name': self.name,
            'hands_played': self.hands_played,
            'vpip': (self.vpip_count / self.hands_played * 100) if self.hands_played > 0 else 0,
            'pfr': (self.pfr_count / self.hands_played * 100) if self.hands_played > 0 else 0,
            'af': self.aggression_factor,
            'notes': self.notes
        }

class Hand(Base):
    __tablename__ = 'hands'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    player_name = Column(String)
    action = Column(String) # e.g., "raise", "call", "fold"
    street = Column(String) # "preflop", "flop", "turn", "river"
    amount = Column(Float, default=0.0)

# Database Setup
engine = create_engine('sqlite:///poker_stats.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def get_session():
    return Session()
