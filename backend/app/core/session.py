"""
Session Manager

Manages negotiation session lifecycle and state.
Uses in-memory storage by default, can be swapped with Redis.
"""
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from decimal import Decimal
from cachetools import TTLCache
import threading

from ..models import (
    ProductData,
    InventoryContext,
    StrategicControls,
    NegotiationStatus,
    NegotiationMode,
    SessionSummary,
)
from ..agents import StrategicPosture, PricingState
from .config import get_settings


@dataclass
class NegotiationSession:
    """Complete state for a negotiation session."""

    session_id: UUID

    # Immutable inputs (locked at creation)
    product: ProductData
    inventory: InventoryContext
    strategy: StrategicControls

    # Computed at creation
    posture: StrategicPosture
    initial_offer: Decimal

    # Mutable state
    status: NegotiationStatus = NegotiationStatus.ACTIVE
    pricing_state: Optional[PricingState] = None

    # Metadata
    buyer_id: Optional[str] = None
    client_ip: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None

    # Audit trail
    final_price: Optional[Decimal] = None
    total_profit: Optional[Decimal] = None

    def __post_init__(self):
        """Initialize pricing state if not provided."""
        if self.pricing_state is None:
            self.pricing_state = PricingState(
                current_round=0,
                current_offer=self.initial_offer,
                buyer_last_offer=None,
                concession_used=Decimal("0"),
                offers_history=[self.initial_offer],
                buyer_history=[],
            )


class SessionManager:
    """
    Thread-safe session storage and management.

    Features:
    - Automatic expiration (TTL)
    - Per-client session limits
    - Session lookup and update
    """

    def __init__(self):
        settings = get_settings()
        self._ttl = settings.session_ttl_seconds
        self._max_per_client = settings.max_sessions_per_client

        # TTLCache automatically expires entries
        self._sessions: TTLCache = TTLCache(
            maxsize=10000,  # Max total sessions
            ttl=self._ttl,
        )

        # Track sessions per client IP
        self._client_sessions: Dict[str, set] = {}

        self._lock = threading.Lock()

    def create_session(
        self,
        product: ProductData,
        inventory: InventoryContext,
        strategy: StrategicControls,
        posture: StrategicPosture,
        initial_offer: Decimal,
        buyer_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> NegotiationSession:
        """Create and store a new negotiation session."""
        session_id = uuid4()

        session = NegotiationSession(
            session_id=session_id,
            product=product,
            inventory=inventory,
            strategy=strategy,
            posture=posture,
            initial_offer=initial_offer,
            buyer_id=buyer_id,
            client_ip=client_ip,
        )

        with self._lock:
            # Check client session limit
            if client_ip:
                self._enforce_client_limit(client_ip, session_id)

            # Store session
            self._sessions[session_id] = session

        return session

    def get_session(self, session_id: UUID) -> Optional[NegotiationSession]:
        """Retrieve a session by ID."""
        return self._sessions.get(session_id)

    def update_session(self, session: NegotiationSession) -> None:
        """Update an existing session."""
        session.updated_at = datetime.utcnow()
        self._sessions[session.session_id] = session

    def close_session(
        self,
        session_id: UUID,
        status: NegotiationStatus,
        final_price: Optional[Decimal] = None,
        total_profit: Optional[Decimal] = None,
    ) -> Optional[NegotiationSession]:
        """Close a session with final outcome."""
        session = self.get_session(session_id)
        if session is None:
            return None

        session.status = status
        session.closed_at = datetime.utcnow()
        session.updated_at = datetime.utcnow()
        session.final_price = final_price
        session.total_profit = total_profit

        self.update_session(session)

        # Remove from client tracking
        if session.client_ip:
            with self._lock:
                if session.client_ip in self._client_sessions:
                    self._client_sessions[session.client_ip].discard(session_id)

        return session

    def get_session_summary(self, session_id: UUID) -> Optional[SessionSummary]:
        """Get summary for a session."""
        session = self.get_session(session_id)
        if session is None:
            return None

        # Calculate profit margin if deal closed
        profit_margin = None
        if session.final_price and session.product.cost_price:
            profit = session.final_price - session.product.cost_price
            if session.final_price > 0:
                profit_margin = (profit / session.final_price) * 100

        return SessionSummary(
            session_id=session.session_id,
            status=session.status,
            mode=session.strategy.mode,
            initial_offer_price=session.initial_offer,
            final_price=session.final_price,
            rounds_taken=session.pricing_state.current_round if session.pricing_state else 0,
            total_profit=session.total_profit,
            profit_margin_percentage=profit_margin,
            created_at=session.created_at,
            updated_at=session.updated_at,
            closed_at=session.closed_at,
        )

    def get_active_count(self) -> int:
        """Get count of active sessions."""
        return len(self._sessions)

    def get_client_session_count(self, client_ip: str) -> int:
        """Get number of active sessions for a client."""
        if client_ip not in self._client_sessions:
            return 0

        # Clean up expired session IDs
        valid_sessions = set()
        for sid in self._client_sessions[client_ip]:
            if sid in self._sessions:
                valid_sessions.add(sid)

        self._client_sessions[client_ip] = valid_sessions
        return len(valid_sessions)

    def _enforce_client_limit(self, client_ip: str, new_session_id: UUID) -> None:
        """Enforce per-client session limit."""
        if client_ip not in self._client_sessions:
            self._client_sessions[client_ip] = set()

        # Clean up expired sessions
        valid = {sid for sid in self._client_sessions[client_ip] if sid in self._sessions}
        self._client_sessions[client_ip] = valid

        # Check limit
        if len(valid) >= self._max_per_client:
            # Remove oldest session
            oldest_id = min(
                valid,
                key=lambda sid: self._sessions[sid].created_at
                if sid in self._sessions else datetime.min
            )
            if oldest_id in self._sessions:
                del self._sessions[oldest_id]
            valid.discard(oldest_id)

        # Add new session
        self._client_sessions[client_ip].add(new_session_id)


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
