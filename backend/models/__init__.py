from .database import Base, engine, get_db

# Re-export every model class from the focused domain modules.
# `models.py` is now a thin compatibility shim that does the same.
from .users import *  # noqa: F401,F403
from .organizations import *  # noqa: F401,F403
from .creators import *  # noqa: F401,F403
from .catalog import *  # noqa: F401,F403
from .works import *  # noqa: F401,F403
from .releases import *  # noqa: F401,F403
from .contracts import *  # noqa: F401,F403
from .royalties import *  # noqa: F401,F403
from .financials import *  # noqa: F401,F403
from .analytics import *  # noqa: F401,F403
from .integrations import *  # noqa: F401,F403
from .notifications import *  # noqa: F401,F403
from .sharing import *  # noqa: F401,F403
from .misc import *  # noqa: F401,F403

from .users import User, UserSession
from .organizations import (
    Organization, OrganizationMember,
    OrganizationType, OrganizationMemberRole, AccountType,
)
from .creators import (
    Creator, CreatorContact, CreativeContact, SharedContactLink, ClientSharedContact,
    CreatorRole, CreditRole, CreatorContactRole, ContributorType,
)
from .catalog import (
    Song, SongCredit, SongDSPLink, ChecklistItem, SongChecklistStatus,
    SongValuationSnapshot, Songwriter, Catalog, Settings, SongEditHistory,
    DSPPlatform, ChecklistStatus, ChecklistCategory,
)
from .works import Work, WorkFolder, WorkTrack, WorkCredit
from .releases import Release, ReleaseTrack, ReleaseType, ReleaseStatus
from .contracts import (
    Contract, ContractParty, ContractAsset, ContractDocument, RightsSplit,
    SongContract, AccountLink,
    ContractType, ContractStatus, AssetType, IPAssetType, RightsType, PartyRole,
    PRO, AccountLinkStatus, AccountLinkPermission,
)
from .royalties import (
    RoyaltyStatement, RoyaltyTransaction, RoyaltyAllocation, Payment, Fee, Advance,
    Payee, RoyaltyStatementLine, RoyaltyProcessingRun, RoyaltyLedgerEntry,
    PayoutBatch, PayoutItem,
    LegacyStatementStatus, StatementStatus, TransactionMatchStatus, PaymentStatus,
    FeeType, PayeeType, RecoupmentPool, PayoutStatus,
)
from .financials import Expense, ExpenseCategory, Placement
from .analytics import (
    Analytics, SongStreamingMetrics, TerritoryRevenue, ValuationCalculation,
    ChartSource, ChartEntry, StreamEstimate, CreatorCreditsProfile, UnderwritingRun,
    ValuationSource,
)
from .integrations import (
    PlatformIntegration, IntegrationAccount, AudioAsset, AudioAnalysis,
    AudioTag, AudioAssetTag, CreatorStorageLink, StorageScanResult, SpotifyOAuthToken,
    StorageProvider, AudioFileType, AnalysisStatus, TagType, TagSource,
    ScanStatus, MatchConfidence,
)
from .notifications import (
    Notification, NotificationPreference, OrgNotificationSetting,
    EmailDigestPreference, ActionItem, PushSubscription,
)
from .sharing import (
    ClientShare, AuditLog, RegistrationReport, AccountMergeRequest, SharedItem,
    ClientShareStatus, ClientShareRole, SharedItemType, SharedItemStatus,
)
from .misc import (
    AIUsageLog, SupportTicket, SupportTicketAttachment, Lead,
    ScheduleAImport, RuntimeConfig, DeployEvent, SavedQuery, QueryHistoryEntry,
    TicketCategory, TicketStatus, LeadType,
)
