from sqlalchemy import Column, Float, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UserTasteProfile(Base):
    __tablename__ = "user_taste_profile"

    user_id = Column(String, primary_key=True)
    dry_mouthfeel = Column(Float)


class SemanticDescriptor(Base):
    __tablename__ = "semantic_descriptors"

    user_id = Column(String, primary_key=True)
    tag = Column(String, primary_key=True)


class PreferenceHistory(Base):
    __tablename__ = "preference_history"

    user_id = Column(String, primary_key=True)
    key = Column(String, primary_key=True)
    value = Column(String)
