<script lang="ts">
	// Parcela de alfalfa dibujada con su geometría real. El color cambia con el rebrote:
	// recién cortada (rastrojo claro) -> verde intenso al acercarse a los GDD necesarios para el
	// siguiente corte; en reposo invernal, tono pajizo. Sustituye a la foto de árboles de la plantilla.
	import type { DigitalTwin } from '$lib/core/Domain';

	export let digitalTwin: DigitalTwin | undefined = undefined;
	export let status: any = null;

	// Mismo valor que GDD_PER_CUT en simulations/harvest_ai_simulation.py
	const GDD_PER_CUT = 580;
	const W = 420;
	const H = 300;
	const PAD = 24;

	$: twin = status?.digitalTwin;
	$: stage = twin?.crop_stage as string | undefined;
	$: gdd = Number(twin?.gdd_accumulated ?? 0);
	$: progress = Math.max(0, Math.min(1, gdd / GDD_PER_CUT));

	const mix = (a: number[], b: number[], t: number) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
	const STUBBLE = [196, 207, 130]; // recién cortada
	const MATURE = [38, 116, 52]; // lista para cortar
	const DORMANT = [190, 176, 140]; // reposo invernal

	$: rgb = !twin ? [150, 170, 140] : stage === 'Dormant' ? DORMANT : mix(STUBBLE, MATURE, progress);
	$: fill = `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;

	const STAGE_LABEL: Record<string, string> = {
		Dormant: 'Reposo invernal',
		Growing: 'Rebrote',
		ReadyToCut: 'Listo para cortar'
	};
	$: stageLabel = stage ? (STAGE_LABEL[stage] ?? stage) : 'Sin simulación';

	// Proyección lon/lat -> SVG (corrigiendo la deformación en longitud por la latitud)
	$: ring = ((digitalTwin?.geometry as any)?.coordinates?.[0] ?? []) as number[][];
	$: points = (() => {
		if (!ring.length) return '';
		const lats = ring.map((p) => p[1]);
		const kx = Math.cos((((Math.min(...lats) + Math.max(...lats)) / 2) * Math.PI) / 180);
		const xs = ring.map((p) => p[0] * kx);
		const minX = Math.min(...xs);
		const minLat = Math.min(...lats);
		const w = Math.max(...xs) - minX || 1e-9;
		const h = Math.max(...lats) - minLat || 1e-9;
		const s = Math.min((W - 2 * PAD) / w, (H - 2 * PAD) / h);
		const offX = (W - w * s) / 2;
		const offY = (H - h * s) / 2;
		return ring
			.map((p, i) => `${(offX + (xs[i] - minX) * s).toFixed(1)},${(H - offY - (p[1] - minLat) * s).toFixed(1)}`)
			.join(' ');
	})();

	$: t = status?.time;
	$: dateLabel = t ? `${t.day}/${t.month}/${t.year ?? ''}` : '--';
	$: temp = status?.weather?.temperature;
	const id = `p${Math.random().toString(36).slice(2, 8)}`;
</script>

<div class="wrap">
	<svg viewBox="0 0 {W} {H}" role="img" aria-label="Parcela de alfalfa">
		<defs>
			<clipPath id="clip-{id}"><polygon {points} /></clipPath>
			<pattern id="rows-{id}" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(18)">
				<rect width="9" height="9" fill="transparent" />
				<rect width="4" height="9" fill="rgba(0,0,0,0.10)" />
			</pattern>
		</defs>
		<rect width={W} height={H} fill="#e7efdd" rx="8" />
		{#if points}
			<polygon {points} {fill} stroke="#2f4f2f" stroke-width="2" stroke-linejoin="round" style="transition: fill 0.4s" />
			<rect width={W} height={H} fill="url(#rows-{id})" clip-path="url(#clip-{id})" />
		{/if}
	</svg>
	<div class="info">
		<div class="row"><strong>{stageLabel}</strong><span>{dateLabel}{temp !== undefined ? ` · ${Number(temp).toFixed(1)} °C` : ''}</span></div>
		<div class="bar" title="Grados-día acumulados desde el último corte">
			<div class="bar-fill" style="width: {progress * 100}%"></div>
		</div>
		<div class="row small">
			<span>GDD {gdd.toFixed(0)} / {GDD_PER_CUT} para el próximo corte</span>
			<span>Corte nº {twin?.cut_number ?? '--'}</span>
		</div>
		<div class="row small">
			<span>Lluvia desde el corte: {Math.round(twin?.prec_accumulated ?? 0)} mm</span>
			<span>Edad: {Number(twin?.stand_age_years ?? 0).toFixed(1)} años</span>
		</div>
	</div>
</div>

<style>
	.wrap {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	svg {
		width: 100%;
		height: auto;
		max-height: 340px;
	}
	.row {
		display: flex;
		justify-content: space-between;
		gap: 1rem;
	}
	.small {
		font-size: 0.85rem;
		opacity: 0.8;
	}
	.bar {
		height: 10px;
		border-radius: 5px;
		background: #d9e2cf;
		overflow: hidden;
		margin: 0.25rem 0;
	}
	.bar-fill {
		height: 100%;
		background: linear-gradient(90deg, #b5c76a, #2f7d3a);
		transition: width 0.4s;
	}
</style>
