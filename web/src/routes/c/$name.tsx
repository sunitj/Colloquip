import { createFileRoute, Outlet } from '@tanstack/react-router';

export const Route = createFileRoute('/c/$name')({
  component: CommunityLayout,
});

function CommunityLayout() {
  return <Outlet />;
}
