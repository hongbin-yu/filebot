"""
AI+人工混合分类系统
当AI无法分类时（置信度低），文档移至待人工分类目录
"""

import logging
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
from sqlalchemy.orm import Session

from ..models.document import Document, DocumentType
from ..models.folder import Folder
from ..models.drawer import Drawer
from ..models.app import App
from .ai_classifier import AIClassifier, AICategory

logger = logging.getLogger(__name__)

# 使用Document模型中的ClassificationStatus枚举
from ..models.document import ClassificationStatus

class HybridClassifier:
    """AI+人工混合分类器"""
    
    def __init__(
        self, 
        ollama_url: str = "http://localhost:11434", 
        default_model: str = "llama3.1:latest",
        ai_confidence_threshold: float = 0.7,  # AI分类置信度阈值
        review_threshold: float = 0.5  # 需要审核的置信度阈值
    ):
        self.ai_classifier = AIClassifier(ollama_url, default_model)
        self.ai_confidence_threshold = ai_confidence_threshold
        self.review_threshold = review_threshold
        
    def classify_document_with_fallback(
        self, 
        document: Document, 
        db: Session, 
        extract_text: bool = True,
        auto_move_to_manual: bool = True
    ) -> Dict[str, Any]:
        """
        分类文档，支持AI+人工回退
        
        Args:
            document: 文档对象
            db: 数据库会话
            extract_text: 是否从文档文件提取文本
            auto_move_to_manual: 是否自动移动到待人工分类目录
            
        Returns:
            包含分类结果和状态的信息
        """
        # 首先尝试AI分类
        ai_result = self.ai_classifier.classify_document(document, db, extract_text)
        
        classification_status = ClassificationStatus.UNCLASSIFIED
        needs_manual = False
        review_needed = False
        
        if ai_result["success"]:
            confidence = ai_result.get("confidence", 0.0)
            
            if confidence >= self.ai_confidence_threshold:
                # AI分类置信度高，直接使用
                classification_status = ClassificationStatus.AI_CLASSIFIED
                logger.info(f"文档 {document.id} AI分类成功，置信度: {confidence:.2f}")
                
                # 更新文档AI字段
                self._update_document_classification(
                    document, db, ai_result, classification_status
                )
                
            elif confidence >= self.review_threshold:
                # 置信度中等，标记为需要审核
                classification_status = ClassificationStatus.REVIEW_NEEDED
                review_needed = True
                logger.info(f"文档 {document.id} AI分类置信度中等，需要审核: {confidence:.2f}")
                
                # 更新文档但标记为需要审核
                self._update_document_classification(
                    document, db, ai_result, classification_status
                )
                
            else:
                # 置信度低，需要人工分类
                classification_status = ClassificationStatus.NEEDS_MANUAL
                needs_manual = True
                logger.info(f"文档 {document.id} AI分类置信度低，需要人工分类: {confidence:.2f}")
                
                # 更新文档状态
                self._update_document_classification(
                    document, db, ai_result, classification_status
                )
                
                # 如果启用自动移动，则移动到待人工分类目录
                if auto_move_to_manual:
                    self._move_to_manual_classification_folder(document, db)
        else:
            # AI分类失败，需要人工分类
            classification_status = ClassificationStatus.NEEDS_MANUAL
            needs_manual = True
            logger.warning(f"文档 {document.id} AI分类失败，需要人工分类")
            
            # 更新文档状态
            self._update_document_classification(
                document, db, ai_result, classification_status
            )
            
            # 如果启用自动移动，则移动到待人工分类目录
            if auto_move_to_manual:
                self._move_to_manual_classification_folder(document, db)
        
        return {
            "ai_result": ai_result,
            "classification_status": classification_status,
            "needs_manual": needs_manual,
            "review_needed": review_needed,
            "confidence_threshold": self.ai_confidence_threshold,
            "review_threshold": self.review_threshold
        }
    
    def get_or_create_manual_classification_folder(
        self, 
        document: Document,
        db: Session,
        folder_name: str = "待人工分类"
    ) -> Optional[Folder]:
        """
        获取或创建待人工分类文件夹
        
        通过文档找到所属的App，然后在系统Drawer中创建待人工分类文件夹
        
        Args:
            document: 文档对象
            db: 数据库会话
            folder_name: 文件夹名称
            
        Returns:
            文件夹对象
        """
        # 获取文档当前的文件夹
        current_folder = db.query(Folder).filter(Folder.id == document.folder_id).first()
        if not current_folder:
            logger.error(f"文档 {document.id} 的文件夹不存在")
            return None
        
        # 获取文件夹所属的Drawer
        drawer = db.query(Drawer).filter(Drawer.id == current_folder.drawer_id).first()
        if not drawer:
            logger.error(f"文件夹 {current_folder.id} 的抽屉不存在")
            return None
        
        # 获取Drawer所属的App
        app = db.query(App).filter(App.id == drawer.app_id).first()
        if not app:
            logger.error(f"抽屉 {drawer.id} 的应用不存在")
            return None
        
        # 查找或创建系统抽屉（用于存放系统文件夹）
        system_drawer_name = "系统文件夹"
        system_drawer = db.query(Drawer).filter(
            Drawer.app_id == app.id,
            Drawer.name == system_drawer_name
        ).first()
        
        if not system_drawer:
            try:
                system_drawer = Drawer(
                    app_id=app.id,
                    name=system_drawer_name,
                    description="系统自动创建的文件夹，用于存放待人工分类等系统文档",
                    order_index=9998  # 放在最后
                )
                db.add(system_drawer)
                db.commit()
                db.refresh(system_drawer)
                logger.info(f"创建系统抽屉: {system_drawer.id}")
            except Exception as e:
                logger.error(f"创建系统抽屉失败: {e}")
                db.rollback()
                return None
        
        # 查找是否已有待人工分类文件夹
        folder = db.query(Folder).filter(
            Folder.drawer_id == system_drawer.id,
            Folder.name == folder_name,
            Folder.is_system_folder == True
        ).first()
        
        if not folder:
            # 创建新的待人工分类文件夹
            try:
                folder = Folder(
                    drawer_id=system_drawer.id,
                    name=folder_name,
                    path=f"/{app.name}/{system_drawer.name}/{folder_name}",
                    description="AI无法自动分类的文档将移动到此文件夹，等待人工分类",
                    order_index=9999,  # 放在最后
                    is_system_folder=True
                )
                db.add(folder)
                db.commit()
                db.refresh(folder)
                logger.info(f"创建待人工分类文件夹: {folder.id}")
            except Exception as e:
                logger.error(f"创建待人工分类文件夹失败: {e}")
                db.rollback()
                return None
        
        return folder
    
    def _move_to_manual_classification_folder(
        self, 
        document: Document, 
        db: Session
    ) -> bool:
        """
        将文档移动到待人工分类文件夹
        
        Args:
            document: 文档对象
            db: 数据库会话
            
        Returns:
            是否成功
        """
        try:
            # 获取或创建待人工分类文件夹
            manual_folder = self.get_or_create_manual_classification_folder(document, db)
            
            if not manual_folder:
                logger.error(f"无法获取或创建待人工分类文件夹")
                return False
            
            # 更新文档的文件夹
            document.folder_id = manual_folder.id
            db.commit()
            
            logger.info(f"文档 {document.id} 已移动到待人工分类文件夹")
            return True
            
        except Exception as e:
            logger.error(f"移动文档到待人工分类文件夹失败: {e}")
            db.rollback()
            return False
    
    def _update_document_classification(
        self,
        document: Document,
        db: Session,
        ai_result: Dict[str, Any],
        classification_status: ClassificationStatus
    ):
        """
        更新文档的分类信息
        
        Args:
            document: 文档对象
            db: 数据库会话
            ai_result: AI分类结果
            classification_status: 分类状态
        """
        try:
            # 更新AI字段
            if ai_result.get("success"):
                document.ai_category = ai_result.get("ai_category")
                document.ai_confidence = ai_result.get("confidence", 0.0)
                
                # 如果AI分类成功且置信度高，也更新文档类型
                if classification_status == ClassificationStatus.AI_CLASSIFIED:
                    document.type = DocumentType(ai_result.get("document_type", "GENERAL"))
            
            # 更新分类状态字段
            document.classification_status = classification_status
            
            # 记录元数据
            metadata = document.document_metadata or {}
            metadata["classification"] = {
                "status": classification_status.value,
                "timestamp": datetime.now().isoformat(),
                "ai_confidence": ai_result.get("confidence", 0.0),
                "ai_model": ai_result.get("model")
            }
            document.document_metadata = metadata
            
            db.commit()
            logger.debug(f"文档 {document.id} 分类信息已更新")
            
        except Exception as e:
            logger.error(f"更新文档分类信息失败: {e}")
            db.rollback()
    
    def get_documents_needing_manual_classification(
        self,
        db: Session,
        limit: int = 100
    ) -> List[Document]:
        """
        获取需要人工分类的文档列表
        
        基于classification_status字段查询
        
        Args:
            db: 数据库会话
            limit: 返回数量限制
            
        Returns:
            文档列表
        """
        # 查询需要人工分类的文档
        documents = db.query(Document).filter(
            Document.classification_status == ClassificationStatus.NEEDS_MANUAL,
            Document.is_archived == False
        ).limit(limit).all()
        
        return documents
    
    def manual_classify_document(
        self,
        document: Document,
        db: Session,
        category: str,
        confidence: float = 1.0,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        人工分类文档
        
        Args:
            document: 文档对象
            db: 数据库会话
            category: 分类类别
            confidence: 人工分类置信度（默认为1.0）
            notes: 分类备注
            
        Returns:
            分类结果
        """
        try:
            # 更新文档分类信息
            document.ai_category = category
            document.ai_confidence = confidence
            document.type = DocumentType(category.lower())  # 假设category对应DocumentType
            
            # 更新分类状态
            document.classification_status = ClassificationStatus.MANUAL_CLASSIFIED
            
            # 记录人工分类信息
            metadata = document.document_metadata or {}
            manual_classification = metadata.get("manual_classification", {})
            manual_classification.update({
                "timestamp": datetime.now().isoformat(),
                "category": category,
                "confidence": confidence,
                "notes": notes,
                "user_id": "manual"  # TODO: 记录实际用户ID
            })
            metadata["manual_classification"] = manual_classification
            metadata["classification"] = {
                "status": "manual_classified",
                "timestamp": datetime.now().isoformat()
            }
            document.document_metadata = metadata
            
            db.commit()
            
            logger.info(f"文档 {document.id} 已人工分类为: {category}")
            
            return {
                "success": True,
                "document_id": document.id,
                "category": category,
                "confidence": confidence,
                "classification_status": ClassificationStatus.MANUAL_CLASSIFIED.value
            }
            
        except Exception as e:
            logger.error(f"人工分类文档失败: {e}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }

# 全局混合分类器实例
hybrid_classifier = HybridClassifier()