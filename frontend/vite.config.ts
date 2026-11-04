import {defineConfig} from 'vite';
export default defineConfig({build:{outDir:'../static/ui/build',emptyOutDir:true,lib:{entry:'src/main.ts',formats:['es'],fileName:()=> 'snp-ui.js',cssFileName:'snp-ui'},sourcemap:false}});
