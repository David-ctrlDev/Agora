import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { type CurrentUser, getMe, logout } from "../api/auth";

export function useMe() {
  return useQuery<CurrentUser>({
    queryKey: ["me"],
    queryFn: getMe,
    retry: false,
    staleTime: 60_000,
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: logout,
    onSuccess: () => queryClient.clear(),
  });
}
