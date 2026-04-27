from abc import ABC, abstractmethod

"""
データ永続化レイヤーの抽象インターフェイス

※ JSON / DB / 外部ストレージなど
  保存先が変わる場合でも、同じインターフェイスで扱うための基底クラス

Repositoryパターン採用により、永続化方式を変更しても
上位レイヤー（Service, View）は影響を受けない設計となる
"""
class BaseRepositoryInterface(ABC):

    @abstractmethod
    def load(self):
        """
        永続化されたデータを読み込む抽象メソッド

        Returns:
            list[Any] | Any:
                データモデルのリスト、または単一オブジェクト

        Notes:
            - 実装クラスでは JSON / DB / API 等から読み込む
            - デシリアライズや Entity 変換は実装側で行う
        """
        pass

    @abstractmethod
    def save(self, data):
        """
        データを永続化する抽象メソッド

        Args:
            data (Any):
                保存するデータ（Entity / dict / listなど）

        Notes:
            - 実装クラスでは JSON / DB / API 等に保存する
            - シリアライズ、ファイル操作等は実装側に委譲
        """
        pass
