"""
Model Registry

Central registry for ML model versioning, storage, and deployment:
- Model versioning and metadata
- Artifact storage (local or cloud)
- Model lifecycle management
- A/B testing support
"""
import os
import json
import pickle
import hashlib
import shutil
from typing import Optional, List, Dict, Any, Type
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum
from abc import ABC, abstractmethod
from loguru import logger


class ModelStage(str, Enum):
    """Model deployment stage."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class ModelStatus(str, Enum):
    """Model status."""
    TRAINING = "training"
    VALIDATING = "validating"
    READY = "ready"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"
    FAILED = "failed"


@dataclass
class ModelMetrics:
    """Model performance metrics."""
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    auc_roc: float = 0.0
    mse: Optional[float] = None
    mae: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ModelMetrics':
        return cls(**data)


@dataclass
class ModelVersion:
    """Model version information."""
    version: str
    model_id: str
    model_name: str
    model_type: str
    created_at: datetime
    created_by: str = "system"
    stage: ModelStage = ModelStage.DEVELOPMENT
    status: ModelStatus = ModelStatus.READY
    description: str = ""
    metrics: ModelMetrics = field(default_factory=ModelMetrics)
    parameters: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    artifact_path: str = ""
    dependencies: List[str] = field(default_factory=list)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if isinstance(self.stage, str):
            self.stage = ModelStage(self.stage)
        if isinstance(self.status, str):
            self.status = ModelStatus(self.status)
        if isinstance(self.metrics, dict):
            self.metrics = ModelMetrics.from_dict(self.metrics)
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
    
    def to_dict(self) -> dict:
        return {
            'version': self.version,
            'model_id': self.model_id,
            'model_name': self.model_name,
            'model_type': self.model_type,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'stage': self.stage.value,
            'status': self.status.value,
            'description': self.description,
            'metrics': self.metrics.to_dict(),
            'parameters': self.parameters,
            'tags': self.tags,
            'artifact_path': self.artifact_path,
            'dependencies': self.dependencies,
            'input_schema': self.input_schema,
            'output_schema': self.output_schema
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ModelVersion':
        return cls(**data)


@dataclass
class RegisteredModel:
    """Registered model with all versions."""
    name: str
    model_type: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    description: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    versions: List[ModelVersion] = field(default_factory=list)
    latest_version: str = ""
    production_version: Optional[str] = None
    staging_version: Optional[str] = None
    
    def get_version(self, version: str) -> Optional[ModelVersion]:
        """Get a specific version."""
        for v in self.versions:
            if v.version == version:
                return v
        return None
    
    def get_production_version(self) -> Optional[ModelVersion]:
        """Get the production version."""
        if self.production_version:
            return self.get_version(self.production_version)
        return None
    
    def add_version(self, version: ModelVersion):
        """Add a new version."""
        self.versions.append(version)
        self.latest_version = version.version
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'model_type': self.model_type,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            'description': self.description,
            'tags': self.tags,
            'versions': [v.to_dict() for v in self.versions],
            'latest_version': self.latest_version,
            'production_version': self.production_version,
            'staging_version': self.staging_version
        }


class ArtifactStore(ABC):
    """Abstract artifact storage backend."""
    
    @abstractmethod
    def save(self, artifact: Any, path: str) -> str:
        """Save artifact and return storage path."""
        pass
    
    @abstractmethod
    def load(self, path: str) -> Any:
        """Load artifact from path."""
        pass
    
    @abstractmethod
    def delete(self, path: str) -> bool:
        """Delete artifact."""
        pass
    
    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if artifact exists."""
        pass


class LocalArtifactStore(ArtifactStore):
    """Local filesystem artifact storage."""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save(self, artifact: Any, path: str) -> str:
        """Save artifact to local filesystem."""
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'wb') as f:
            pickle.dump(artifact, f)
        
        logger.debug(f"Saved artifact to {full_path}")
        return str(full_path)
    
    def load(self, path: str) -> Any:
        """Load artifact from local filesystem."""
        full_path = self.base_path / path if not Path(path).is_absolute() else Path(path)
        
        with open(full_path, 'rb') as f:
            return pickle.load(f)
    
    def delete(self, path: str) -> bool:
        """Delete artifact from filesystem."""
        full_path = self.base_path / path if not Path(path).is_absolute() else Path(path)
        
        try:
            if full_path.is_file():
                full_path.unlink()
            elif full_path.is_dir():
                shutil.rmtree(full_path)
            return True
        except Exception as e:
            logger.error(f"Error deleting artifact: {e}")
            return False
    
    def exists(self, path: str) -> bool:
        """Check if artifact exists."""
        full_path = self.base_path / path if not Path(path).is_absolute() else Path(path)
        return full_path.exists()


class ModelRegistry:
    """
    Central model registry for versioning and lifecycle management.
    
    Features:
    - Model versioning
    - Artifact storage
    - Stage transitions
    - Model comparison
    - Deployment tracking
    """
    
    def __init__(
        self,
        storage_path: str = "./model_registry",
        artifact_store: Optional[ArtifactStore] = None
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.artifact_store = artifact_store or LocalArtifactStore(
            str(self.storage_path / "artifacts")
        )
        
        self.registry_file = self.storage_path / "registry.json"
        self.models: Dict[str, RegisteredModel] = {}
        
        self._load_registry()
    
    def _load_registry(self):
        """Load registry from disk."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                
                for name, model_data in data.items():
                    # Parse dates
                    model_data['created_at'] = datetime.fromisoformat(model_data['created_at'])
                    model_data['updated_at'] = datetime.fromisoformat(model_data['updated_at'])
                    
                    # Parse versions
                    versions = []
                    for v in model_data.get('versions', []):
                        versions.append(ModelVersion.from_dict(v))
                    model_data['versions'] = versions
                    
                    self.models[name] = RegisteredModel(**model_data)
                
                logger.info(f"Loaded {len(self.models)} models from registry")
            except Exception as e:
                logger.error(f"Error loading registry: {e}")
                self.models = {}
    
    def _save_registry(self):
        """Save registry to disk."""
        try:
            data = {name: model.to_dict() for name, model in self.models.items()}
            
            with open(self.registry_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug("Registry saved")
        except Exception as e:
            logger.error(f"Error saving registry: {e}")
    
    def _generate_version(self, model_name: str) -> str:
        """Generate next version number."""
        if model_name not in self.models:
            return "1.0.0"
        
        versions = self.models[model_name].versions
        if not versions:
            return "1.0.0"
        
        # Parse latest version and increment
        latest = versions[-1].version
        parts = latest.split('.')
        
        try:
            major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
            return f"{major}.{minor}.{patch + 1}"
        except (ValueError, IndexError):
            return f"1.0.{len(versions)}"
    
    def _generate_model_id(self, model_name: str, version: str) -> str:
        """Generate unique model ID."""
        hash_input = f"{model_name}_{version}_{datetime.utcnow().isoformat()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:12]
    
    def register_model(
        self,
        model: Any,
        name: str,
        model_type: str,
        description: str = "",
        metrics: Optional[ModelMetrics] = None,
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        version: Optional[str] = None
    ) -> ModelVersion:
        """
        Register a new model version.
        
        Args:
            model: The model object to register
            name: Model name
            model_type: Type of model (e.g., 'lstm', 'random_forest')
            description: Model description
            metrics: Performance metrics
            parameters: Model parameters/hyperparameters
            tags: Optional tags
            version: Optional version (auto-generated if not provided)
            
        Returns:
            ModelVersion object
        """
        version = version or self._generate_version(name)
        model_id = self._generate_model_id(name, version)
        
        # Save model artifact
        artifact_path = f"{name}/{version}/model.pkl"
        self.artifact_store.save(model, artifact_path)
        
        # Create version
        model_version = ModelVersion(
            version=version,
            model_id=model_id,
            model_name=name,
            model_type=model_type,
            created_at=datetime.utcnow(),
            description=description,
            metrics=metrics or ModelMetrics(),
            parameters=parameters or {},
            tags=tags or {},
            artifact_path=artifact_path
        )
        
        # Register or update model
        if name not in self.models:
            self.models[name] = RegisteredModel(
                name=name,
                model_type=model_type,
                description=description,
                tags=tags or {}
            )
        
        self.models[name].add_version(model_version)
        self._save_registry()
        
        logger.info(f"Registered model '{name}' version {version}")
        return model_version
    
    def get_model(self, name: str) -> Optional[RegisteredModel]:
        """Get a registered model by name."""
        return self.models.get(name)
    
    def get_model_version(
        self,
        name: str,
        version: Optional[str] = None
    ) -> Optional[ModelVersion]:
        """Get a specific model version."""
        model = self.models.get(name)
        if not model:
            return None
        
        if version:
            return model.get_version(version)
        return model.get_version(model.latest_version)
    
    def load_model(
        self,
        name: str,
        version: Optional[str] = None,
        stage: Optional[ModelStage] = None
    ) -> Any:
        """
        Load a model from the registry.
        
        Args:
            name: Model name
            version: Specific version (optional)
            stage: Load from specific stage (e.g., production)
            
        Returns:
            Loaded model object
        """
        model = self.models.get(name)
        if not model:
            raise ValueError(f"Model '{name}' not found")
        
        # Determine which version to load
        if stage == ModelStage.PRODUCTION and model.production_version:
            version = model.production_version
        elif stage == ModelStage.STAGING and model.staging_version:
            version = model.staging_version
        elif not version:
            version = model.latest_version
        
        model_version = model.get_version(version)
        if not model_version:
            raise ValueError(f"Version '{version}' not found for model '{name}'")
        
        # Load from artifact store
        artifact = self.artifact_store.load(model_version.artifact_path)
        logger.info(f"Loaded model '{name}' version {version}")
        
        return artifact
    
    def transition_stage(
        self,
        name: str,
        version: str,
        stage: ModelStage
    ) -> bool:
        """
        Transition a model version to a new stage.
        
        Args:
            name: Model name
            version: Version to transition
            stage: Target stage
            
        Returns:
            Success status
        """
        model = self.models.get(name)
        if not model:
            return False
        
        model_version = model.get_version(version)
        if not model_version:
            return False
        
        old_stage = model_version.stage
        model_version.stage = stage
        
        # Update model's stage references
        if stage == ModelStage.PRODUCTION:
            model.production_version = version
        elif stage == ModelStage.STAGING:
            model.staging_version = version
        
        self._save_registry()
        logger.info(f"Transitioned '{name}' v{version} from {old_stage.value} to {stage.value}")
        
        return True
    
    def compare_models(
        self,
        name: str,
        versions: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compare multiple model versions.
        
        Args:
            name: Model name
            versions: List of versions to compare
            
        Returns:
            Comparison dictionary
        """
        model = self.models.get(name)
        if not model:
            return {}
        
        comparison = {}
        for version in versions:
            model_version = model.get_version(version)
            if model_version:
                comparison[version] = {
                    'metrics': model_version.metrics.to_dict(),
                    'parameters': model_version.parameters,
                    'stage': model_version.stage.value,
                    'created_at': model_version.created_at.isoformat()
                }
        
        return comparison
    
    def list_models(
        self,
        model_type: Optional[str] = None,
        stage: Optional[ModelStage] = None
    ) -> List[RegisteredModel]:
        """List all registered models with optional filtering."""
        models = list(self.models.values())
        
        if model_type:
            models = [m for m in models if m.model_type == model_type]
        
        if stage:
            # Filter to models that have versions in the specified stage
            filtered = []
            for model in models:
                for version in model.versions:
                    if version.stage == stage:
                        filtered.append(model)
                        break
            models = filtered
        
        return models
    
    def delete_model_version(self, name: str, version: str) -> bool:
        """Delete a specific model version."""
        model = self.models.get(name)
        if not model:
            return False
        
        model_version = model.get_version(version)
        if not model_version:
            return False
        
        # Delete artifact
        if model_version.artifact_path:
            self.artifact_store.delete(model_version.artifact_path)
        
        # Remove from versions list
        model.versions = [v for v in model.versions if v.version != version]
        
        # Update references
        if model.production_version == version:
            model.production_version = None
        if model.staging_version == version:
            model.staging_version = None
        if model.latest_version == version:
            model.latest_version = model.versions[-1].version if model.versions else ""
        
        self._save_registry()
        logger.info(f"Deleted model '{name}' version {version}")
        
        return True
    
    def delete_model(self, name: str) -> bool:
        """Delete a model and all its versions."""
        if name not in self.models:
            return False
        
        model = self.models[name]
        
        # Delete all artifacts
        for version in model.versions:
            if version.artifact_path:
                self.artifact_store.delete(version.artifact_path)
        
        # Remove from registry
        del self.models[name]
        self._save_registry()
        
        logger.info(f"Deleted model '{name}' and all versions")
        return True
    
    def search_models(
        self,
        query: str = "",
        tags: Optional[Dict[str, str]] = None,
        min_accuracy: Optional[float] = None
    ) -> List[RegisteredModel]:
        """
        Search models by various criteria.
        
        Args:
            query: Search in name and description
            tags: Filter by tags
            min_accuracy: Minimum accuracy threshold
            
        Returns:
            List of matching models
        """
        results = []
        
        for model in self.models.values():
            # Query match
            if query:
                if query.lower() not in model.name.lower() and \
                   query.lower() not in model.description.lower():
                    continue
            
            # Tag match
            if tags:
                if not all(model.tags.get(k) == v for k, v in tags.items()):
                    continue
            
            # Accuracy filter
            if min_accuracy:
                has_passing_version = False
                for version in model.versions:
                    if version.metrics.accuracy >= min_accuracy:
                        has_passing_version = True
                        break
                if not has_passing_version:
                    continue
            
            results.append(model)
        
        return results
    
    def get_production_models(self) -> Dict[str, ModelVersion]:
        """Get all models currently in production."""
        production = {}
        
        for name, model in self.models.items():
            if model.production_version:
                version = model.get_version(model.production_version)
                if version:
                    production[name] = version
        
        return production
    
    def export_model(
        self,
        name: str,
        version: str,
        export_path: str
    ) -> bool:
        """Export a model to a specified path."""
        model_version = self.get_model_version(name, version)
        if not model_version:
            return False
        
        export_dir = Path(export_path)
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy artifact
        artifact = self.artifact_store.load(model_version.artifact_path)
        with open(export_dir / "model.pkl", 'wb') as f:
            pickle.dump(artifact, f)
        
        # Save metadata
        with open(export_dir / "metadata.json", 'w') as f:
            json.dump(model_version.to_dict(), f, indent=2)
        
        logger.info(f"Exported model '{name}' v{version} to {export_path}")
        return True


# Global registry instance
_registry: Optional[ModelRegistry] = None


def get_registry(storage_path: str = "./model_registry") -> ModelRegistry:
    """Get or create the global model registry."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry(storage_path)
    return _registry
