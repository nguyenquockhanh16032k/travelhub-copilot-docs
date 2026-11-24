import { api } from './api'
import type {
  TourAssignment,
  TourAssignmentPage,
  TourAssignmentPayload,
} from '../types/operations'

export async function listAssignments(
  departureId: string,
  page: number,
  size: number,
): Promise<TourAssignmentPage> {
  const response = await api.get<TourAssignmentPage>(
    `/departures/${departureId}/assignments`,
    { params: { page, size } },
  )
  return response.data
}

export async function createAssignment(
  departureId: string,
  payload: TourAssignmentPayload,
): Promise<TourAssignment> {
  const response = await api.post<TourAssignment>(
    `/departures/${departureId}/assignments`,
    payload,
  )
  return response.data
}

export async function updateAssignment(
  departureId: string,
  assignmentId: string,
  payload: TourAssignmentPayload,
): Promise<TourAssignment> {
  const response = await api.patch<TourAssignment>(
    `/departures/${departureId}/assignments/${assignmentId}`,
    payload,
  )
  return response.data
}

export async function deleteAssignment(
  departureId: string,
  assignmentId: string,
): Promise<void> {
  await api.delete(`/departures/${departureId}/assignments/${assignmentId}`)
}
