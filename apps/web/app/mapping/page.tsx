import { DataMappingStudio } from "@/components/data-mapping-studio";
import { PlatformShell } from "@/components/platform-shell";

export const dynamic = "force-dynamic";

export default function MappingPage() {
  return (
    <PlatformShell
      active="/mapping"
      subtitle="Match source and target fields visually with governed transformations, required-field validation, and payload previews."
      title="Data Mapping Studio"
    >
      <DataMappingStudio />
    </PlatformShell>
  );
}
