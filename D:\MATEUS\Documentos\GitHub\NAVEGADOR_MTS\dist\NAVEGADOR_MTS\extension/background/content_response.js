export function requireContentSuccess(response) {
  if (response?.success === false) {
    throw new Error(response.error || 'A ação na página falhou.');
  }
  return response;
}
