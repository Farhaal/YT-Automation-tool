import '@testing-library/jest-dom';

global.fetch = () => Promise.resolve({
  json: () => Promise.resolve({})
}) as Promise<Response>;
