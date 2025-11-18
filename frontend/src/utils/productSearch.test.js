import { buildAssetUrl } from './productSearch';

describe('buildAssetUrl', () => {
  it('encodes nested catalog paths', () => {
    const url = buildAssetUrl('http://localhost:8000', 'data/catalog/My Folder/item 1.jpg');
    expect(url).toBe('http://localhost:8000/asset/catalog/My%20Folder/item%201.jpg');
  });
});
