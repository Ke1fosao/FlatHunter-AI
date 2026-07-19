import { ClusterDetailExtras } from "@/components/cluster-detail-extras";
import { ListingDetails } from "@/components/listing-details";

export default async function ListingPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ profile?: string; cluster?: string }>;
}) {
  const [{ id }, query] = await Promise.all([params, searchParams]);
  return (
    <>
      <ListingDetails listingId={id} />
      <ClusterDetailExtras
        clusterId={query.cluster}
        profileId={query.profile}
      />
    </>
  );
}
