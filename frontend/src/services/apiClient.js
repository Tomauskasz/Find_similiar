import axios from 'axios';

export const createApiClient = (baseURL) =>
  axios.create({
    baseURL,
  });

export const fetchStats = (client, config = {}) =>
  client.get('/stats', {
    timeout: 3000,
    ...config,
  });

export const searchSimilar = (client, formData, config = {}) =>
  client.post('/search', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    ...config,
  });
