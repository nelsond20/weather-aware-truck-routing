import type { Preview } from '@storybook/react-vite';
import { mswLoader } from 'msw-storybook-addon/csf3';
import { setupWorker } from 'msw/browser';
import '../src/styles/tokens.css';
import '../src/styles/reset.css';
import '../src/styles/globals.css';
const loader=mswLoader(async()=>{const worker=setupWorker();await worker.start({quiet:true,onUnhandledRequest(request,print){if(new URL(request.url).pathname.startsWith('/api/'))print.error();}});return worker;});
const preview: Preview = { loaders: [loader], parameters: { a11y: { test: 'error' } } };
export default preview;
