from __future__ import annotations

from typing import Any, cast

from django.db.models import Case, IntegerField, Prefetch, QuerySet, When
from django.shortcuts import get_object_or_404
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.models import User
from apps.duplicates.candidates import confirm_candidate, restore_candidate_auto, split_candidate
from apps.duplicates.clustering import rebuild_clusters
from apps.duplicates.models import (
    ClusterMemberRole,
    ClusterStatus,
    DuplicateCandidate,
    ListingCluster,
    ListingClusterMember,
    UserClusterState,
)
from apps.duplicates.serializers import (
    CandidateReviewSerializer,
    ClusterStateMutationSerializer,
    DuplicateCandidateSerializer,
    ListingClusterDetailSerializer,
)
from apps.duplicates.services import ComparisonLimitError, update_cluster_state
from apps.searches.models import SearchProfile

_PRIMARY_FIRST = Case(
    When(role=ClusterMemberRole.PRIMARY, then=0),
    default=1,
    output_field=IntegerField(),
)


class ClusterDetailQuerySerializer(serializers.Serializer):
    profile_id = serializers.UUIDField(required=False)


class ListingClusterViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ListingClusterDetailSerializer

    def get_queryset(self) -> QuerySet[ListingCluster]:
        user = cast(User, self.request.user)
        members = ListingClusterMember.objects.select_related(
            "listing",
            "listing__source",
        ).order_by(_PRIMARY_FIRST, "-confidence", "-listing__published_at")
        states = UserClusterState.objects.filter(user=user)
        return (
            ListingCluster.objects.filter(status=ClusterStatus.ACTIVE)
            .select_related("primary_listing", "primary_listing__source")
            .prefetch_related(
                Prefetch("members", queryset=members, to_attr="current_members"),
                Prefetch("user_states", queryset=states, to_attr="current_user_cluster_states"),
            )
        )

    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        cluster = self.get_object()
        query = ClusterDetailQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        profile = None
        profile_id = query.validated_data.get("profile_id")
        if profile_id is not None:
            profile = get_object_or_404(
                SearchProfile,
                id=profile_id,
                user=cast(User, request.user),
            )
        serializer = self.get_serializer(cluster, context={"request": request, "profile": profile})
        return Response(serializer.data)

    @action(detail=True, methods=["patch"])
    def state(self, request: Request, pk: str | None = None) -> Response:
        cluster = self.get_object()
        serializer = ClusterStateMutationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            state = update_cluster_state(
                cluster=cluster,
                user=cast(User, request.user),
                values=dict(serializer.validated_data),
            )
        except ComparisonLimitError as error:
            return Response(
                {"error": {"code": "comparison_limit", "message": str(error)}},
                status=status.HTTP_409_CONFLICT,
            )
        cluster.current_user_cluster_states = [state]
        return Response(
            self.get_serializer(cluster, context={"request": request, "profile": None}).data
        )


class DuplicateCandidateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DuplicateCandidateSerializer
    permission_classes = (IsAdminUser,)
    filterset_fields = ()

    def get_queryset(self) -> QuerySet[DuplicateCandidate]:
        return DuplicateCandidate.objects.select_related(
            "left_listing",
            "left_listing__source",
            "right_listing",
            "right_listing__source",
            "reviewed_by",
        )

    def _review(self, request: Request, operation: str) -> Response:
        candidate = self.get_object()
        serializer = CandidateReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = serializer.validated_data.get("note", "")
        actor = cast(User, request.user)
        if operation == "confirm":
            candidate = confirm_candidate(candidate, actor=actor, note=note)
        elif operation == "split":
            candidate = split_candidate(candidate, actor=actor, note=note)
        else:
            candidate = restore_candidate_auto(candidate, actor=actor, note=note)
        rebuild_clusters(city=candidate.left_listing.city)
        return Response(self.get_serializer(candidate).data)

    @action(detail=True, methods=["post"])
    def confirm(self, request: Request, pk: str | None = None) -> Response:
        return self._review(request, "confirm")

    @action(detail=True, methods=["post"])
    def split(self, request: Request, pk: str | None = None) -> Response:
        return self._review(request, "split")

    @action(detail=True, methods=["post"])
    def restore(self, request: Request, pk: str | None = None) -> Response:
        return self._review(request, "restore")
