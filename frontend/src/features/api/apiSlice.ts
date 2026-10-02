import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

// Types alignés sur backend/app/routers/items.py
export interface ItemCreate {
  name: string;
  tier: string;
}

export interface Item extends ItemCreate {
  id: number;
}

export interface Health {
  status: string;
}

export const apiSlice = createApi({
  reducerPath: 'api',
  // '/api' est redirigé vers le backend FastAPI par le proxy Vite (vite.config.ts)
  baseQuery: fetchBaseQuery({ baseUrl: '/api' }),
  tagTypes: ['Item'],
  endpoints: (builder) => ({
    getHealth: builder.query<Health, void>({
      query: () => '/health',
    }),
    getItems: builder.query<Item[], void>({
      query: () => '/items/',
      providesTags: ['Item'],
    }),
    addItem: builder.mutation<Item, ItemCreate>({
      query: (body) => ({ url: '/items/', method: 'POST', body }),
      invalidatesTags: ['Item'],
    }),
  }),
});

export const { useGetHealthQuery, useGetItemsQuery, useAddItemMutation } = apiSlice;
