from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import DigitalAsset, Price, Product
from ..serializers import (
    SellerAssetSerializer,
    SellerPriceSerializer,
    SellerProductSerializer,
    ServiceOfferSerializer,
    ServiceOfferUpsertSerializer,
)
from .helpers import get_request_profile


class SellerProductListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SellerProductSerializer

    def get_queryset(self):
        profile = get_request_profile(self.request)
        return Product.objects.filter(owner=profile).select_related("active_price", "service_offer")

    def perform_create(self, serializer):
        profile = get_request_profile(self.request)
        serializer.save(owner=profile)


class SellerProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SellerProductSerializer

    def get_queryset(self):
        profile = get_request_profile(self.request)
        return Product.objects.filter(owner=profile).select_related("active_price", "service_offer")


class SellerPriceListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SellerPriceSerializer

    def _get_product(self):
        profile = get_request_profile(self.request)
        return get_object_or_404(Product, pk=self.kwargs["product_id"], owner=profile)

    def get_queryset(self):
        return Price.objects.filter(product=self._get_product()).order_by("amount_cents", "id")

    def perform_create(self, serializer):
        product = self._get_product()
        price = serializer.save(product=product)

        if price.is_default:
            Price.objects.filter(product=product).exclude(pk=price.pk).update(is_default=False)
            product.active_price = price
            product.save(update_fields=["active_price", "updated_at"])
        elif product.active_price_id is None:
            product.active_price = price
            product.save(update_fields=["active_price", "updated_at"])


class SellerPriceDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SellerPriceSerializer

    def get_queryset(self):
        profile = get_request_profile(self.request)
        return Price.objects.filter(product__owner=profile).select_related("product")

    def perform_update(self, serializer):
        price = serializer.save()
        product = price.product
        if price.is_default:
            Price.objects.filter(product=product).exclude(pk=price.pk).update(is_default=False)
            if product.active_price_id != price.id:
                product.active_price = price
                product.save(update_fields=["active_price", "updated_at"])


class SellerAssetListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SellerAssetSerializer

    def _get_product(self):
        profile = get_request_profile(self.request)
        return get_object_or_404(Product, pk=self.kwargs["product_id"], owner=profile)

    def get_queryset(self):
        return DigitalAsset.objects.filter(product=self._get_product()).order_by("title", "id")

    def perform_create(self, serializer):
        serializer.save(product=self._get_product())


class SellerAssetDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SellerAssetSerializer

    def get_queryset(self):
        profile = get_request_profile(self.request)
        return DigitalAsset.objects.filter(product__owner=profile).select_related("product")


class SellerServiceOfferView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, product_id):
        profile = get_request_profile(request)
        product = get_object_or_404(Product, pk=product_id, owner=profile)
        if product.product_type != Product.ProductType.SERVICE:
            return Response({"detail": "Product is not a service product."}, status=400)

        if not hasattr(product, "service_offer"):
            return Response({"detail": "No service offer configured yet."}, status=404)

        return Response(ServiceOfferSerializer(product.service_offer).data)

    def put(self, request, product_id):
        return self._upsert(request, product_id)

    def patch(self, request, product_id):
        return self._upsert(request, product_id, partial=True)

    def _upsert(self, request, product_id, partial=False):
        profile = get_request_profile(request)
        product = get_object_or_404(Product, pk=product_id, owner=profile)
        if product.product_type != Product.ProductType.SERVICE:
            return Response({"detail": "Product is not a service product."}, status=400)

        service_offer = getattr(product, "service_offer", None)
        serializer = ServiceOfferUpsertSerializer(
            service_offer,
            data={**request.data, "product": product.id},
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        offer = serializer.save(product=product)
        return Response(ServiceOfferSerializer(offer).data)
