<template>
	<div class="checkout-page">
		<header class="nav">
			<div class="nav-inner">
				<router-link to="/welcome" class="brand" aria-label="proNotify home">
					<img :src="logo" alt="proNotify" />
				</router-link>
				<nav class="nav-links" aria-label="Checkout navigation">
					<router-link to="/welcome">Home</router-link>
					<a :href="LEGAL_LINKS.terms">Terms</a>
					<a :href="LEGAL_LINKS.refund">Refunds</a>
					<a :href="LEGAL_LINKS.privacy">Privacy</a>
					<a :href="LEGAL_LINKS.contact">Contact</a>
				</nav>
				<div class="nav-actions">
					<router-link to="/login" class="btn ghost">Sign in</router-link>
				</div>
			</div>
		</header>

		<main class="wrap">
			<div class="head">
				<span class="eyebrow">Secure checkout</span>
				<h1>Review your proNotify plan</h1>
				<p>Confirm your plan and billing details, then create your account to continue to PromptPay payment.</p>
			</div>

			<div class="grid">
				<section class="card order" aria-label="Order summary">
					<h2>Order summary</h2>
					<div class="product">
						<div class="product-mark">PN</div>
						<div class="product-copy">
							<b>{{ plan.name }}</b>
							<small>{{ plan.billingDays }} days of workspace access</small>
						</div>
						<div class="product-price">{{ formatTHB(plan.priceTHB) }}</div>
					</div>

					<dl class="lines">
						<div><dt>Billing cycle</dt><dd>{{ plan.billingDays }} days</dd></div>
						<div><dt>Price</dt><dd>{{ formatTHB(plan.priceTHB) }} THB</dd></div>
						<div><dt>Auto-renewal</dt><dd>Not enabled</dd></div>
						<div><dt>Payment method</dt><dd>{{ plan.paymentMethod }}</dd></div>
						<div><dt>Currency</dt><dd>THB (Thai Baht)</dd></div>
					</dl>

					<div class="total">
						<span>Total due today</span>
						<b>{{ formatTHB(plan.priceTHB) }}</b>
					</div>

					<div class="actions">
						<router-link to="/signup" class="btn primary wide">Create account &amp; continue</router-link>
						<router-link to="/login" class="btn ghost wide">Already have an account? Sign in</router-link>
					</div>
					<p class="fine">
						After email verification you will be taken to a secure Omise PromptPay page to complete payment. Your plan activates after the payment is confirmed.
					</p>
				</section>

				<aside class="side">
					<section class="card">
						<h2>What happens next</h2>
						<ol class="steps">
							<li><span>1</span><div><b>Create your account</b><small>Enter your email, company name and password.</small></div></li>
							<li><span>2</span><div><b>Verify your email</b><small>Click the verification link sent to your inbox.</small></div></li>
							<li><span>3</span><div><b>Scan the PromptPay QR</b><small>Pay {{ formatTHB(plan.priceTHB) }} securely through Omise.</small></div></li>
							<li><span>4</span><div><b>Start adding properties</b><small>Your workspace is ready once payment is confirmed.</small></div></li>
						</ol>
					</section>

					<section class="card terms">
						<h2>Auto-renewal &amp; cancellation</h2>
						<p><b>No auto-renewal.</b> This is a one-time payment for {{ plan.billingDays }} days. proNotify does not store your payment details and will not charge you automatically.</p>
						<p>Your plan ends after {{ plan.billingDays }} days. To continue, you can manually purchase another term. You may cancel future renewal by emailing <a :href="`mailto:${BUSINESS.email}`">{{ BUSINESS.email }}</a> at least 7 days before the end of the current term. Access continues until the end of the paid term.</p>
						<p>Refunds are handled under our <a :href="LEGAL_LINKS.refund">Cancellation &amp; Refund Policy</a>. Approved refunds are returned to the original payment method via Omise.</p>
					</section>

					<section class="card contact">
						<h2>Billing contact</h2>
						<p>{{ BUSINESS.legalName }}<br />{{ BUSINESS.address }}<br />Phone: {{ BUSINESS.phone }}<br />Email: <a :href="`mailto:${BUSINESS.email}`">{{ BUSINESS.email }}</a></p>
						<p class="muted">Support hours: {{ BUSINESS.hours }}</p>
					</section>
				</aside>
			</div>

			<footer class="policy-strip">
				<span>By continuing you agree to:</span>
				<a :href="LEGAL_LINKS.terms">Terms of Service</a>
				<a :href="LEGAL_LINKS.refund">Cancellation &amp; Refund Policy</a>
				<a :href="LEGAL_LINKS.privacy">Privacy Policy</a>
			</footer>
		</main>

		<footer class="footer">
			<div class="footer-inner">
				<span>© 2026–2028 proNotify. All rights reserved.</span>
				<span>{{ BUSINESS.legalName }} · {{ BUSINESS.address }} · {{ BUSINESS.email }}</span>
			</div>
		</footer>
	</div>
</template>

<script setup lang="ts" name="publicCheckout">
import { onMounted, ref } from 'vue';
import logo from '/@/assets/img/proNotify_logo_trans.png';
import { NextLoading } from '/@/utils/loading';
import { BUSINESS, PLAN, LEGAL_LINKS, formatTHB, fetchPublicPlan } from '/@/views/public/business';

const plan = ref({ ...PLAN });

onMounted(async () => {
	NextLoading.done();
	document.title = 'Checkout — proNotify Annual Plan';
	plan.value = await fetchPublicPlan();
});
</script>

<style scoped lang="scss">
.checkout-page {
	--pn-bg: #1f1f1f;
	--pn-card: #1a1a1c;
	--pn-card-2: #222225;
	--pn-border: #333337;
	--pn-text: #e8e8ea;
	--pn-muted: #b1b4b8;
	--pn-faint: #8f9297;
	--pn-primary: #409eff;
	--pn-primary-hover: #66b1ff;
	--pn-green: #67c23a;

	min-height: 100dvh;
	background: var(--pn-bg);
	color: var(--pn-text);
	font-family: 'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans Thai', sans-serif;
	font-size: 15px;
	line-height: 1.65;
}

.checkout-page a {
	color: inherit;
	text-decoration: none;
}

.nav {
	position: sticky;
	top: 0;
	z-index: 20;
	background: rgba(31, 31, 31, 0.9);
	border-bottom: 1px solid rgba(255, 255, 255, 0.06);
	backdrop-filter: blur(14px);
}

.nav-inner {
	display: flex;
	align-items: center;
	gap: 24px;
	max-width: 1120px;
	margin: 0 auto;
	padding: 16px 24px;
}

.brand img {
	display: block;
	width: 150px;
	height: auto;
}

.nav-links {
	display: flex;
	gap: 20px;
	color: var(--pn-muted);
	font-size: 14px;
}

.nav-links a:hover {
	color: var(--pn-text);
}

.nav-actions {
	margin-left: auto;
}

.btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	border: 1px solid transparent;
	border-radius: 10px;
	padding: 11px 18px;
	font-size: 14px;
	font-weight: 600;
	line-height: 1.2;
	transition: background 0.18s ease, border-color 0.18s ease;
}

.btn.primary {
	background: var(--pn-primary);
	border-color: var(--pn-primary);
	color: #fff;
}

.btn.primary:hover {
	background: var(--pn-primary-hover);
	border-color: var(--pn-primary-hover);
}

.btn.ghost {
	border-color: var(--pn-border);
	color: var(--pn-text);
}

.btn.ghost:hover {
	background: rgba(255, 255, 255, 0.04);
	border-color: #4a4a50;
}

.btn.wide {
	width: 100%;
}

.wrap {
	max-width: 1120px;
	margin: 0 auto;
	padding: 56px 24px 64px;
}

.head {
	max-width: 720px;
	margin-bottom: 34px;
}

.eyebrow {
	display: inline-block;
	margin-bottom: 12px;
	color: #8ec5ff;
	font-size: 12px;
	font-weight: 700;
	letter-spacing: 0.12em;
	text-transform: uppercase;
}

.head h1 {
	margin: 0;
	font-size: clamp(30px, 4vw, 44px);
	line-height: 1.1;
	letter-spacing: -0.02em;
}

.head p {
	margin: 14px 0 0;
	color: var(--pn-muted);
	font-size: 15px;
}

.grid {
	display: grid;
	grid-template-columns: minmax(0, 1fr) minmax(0, 1.05fr);
	gap: 20px;
	align-items: start;
}

.card {
	background: var(--pn-card);
	border: 1px solid var(--pn-border);
	border-radius: 16px;
	padding: 24px;
}

.card + .card {
	margin-top: 16px;
}

.card h2 {
	margin: 0 0 18px;
	font-size: 16px;
}

.order h2 {
	font-size: 20px;
}

.product {
	display: flex;
	align-items: center;
	gap: 14px;
	padding-bottom: 20px;
	border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.product-mark {
	flex: 0 0 auto;
	display: grid;
	place-items: center;
	width: 46px;
	height: 46px;
	border-radius: 12px;
	background: rgba(64, 158, 255, 0.14);
	border: 1px solid rgba(64, 158, 255, 0.28);
	color: #9ec9ff;
	font-size: 13px;
	font-weight: 700;
}

.product-copy {
	min-width: 0;
}

.product-copy b {
	display: block;
	font-size: 16px;
}

.product-copy small {
	display: block;
	margin-top: 3px;
	color: var(--pn-faint);
	font-size: 12px;
}

.product-price {
	margin-left: auto;
	font-size: 22px;
	font-weight: 700;
	white-space: nowrap;
}

.lines {
	margin: 0;
	padding: 20px 0;
	display: grid;
	gap: 12px;
	border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.lines > div {
	display: flex;
	justify-content: space-between;
	gap: 18px;
}

.lines dt {
	color: var(--pn-muted);
	font-size: 14px;
}

.lines dd {
	margin: 0;
	font-size: 14px;
	text-align: right;
}

.total {
	display: flex;
	align-items: baseline;
	justify-content: space-between;
	gap: 18px;
	padding: 20px 0;
}

.total span {
	color: var(--pn-muted);
	font-size: 14px;
}

.total b {
	font-size: 28px;
}

.actions {
	display: grid;
	gap: 10px;
}

.fine {
	margin: 14px 0 0;
	color: var(--pn-faint);
	font-size: 12px;
	text-align: center;
}

.side .card h2 {
	font-size: 17px;
}

.steps {
	margin: 0;
	padding: 0;
	list-style: none;
	display: grid;
	gap: 14px;
}

.steps li {
	display: flex;
	gap: 12px;
}

.steps li > span {
	flex: 0 0 auto;
	display: grid;
	place-items: center;
	width: 26px;
	height: 26px;
	border-radius: 99px;
	background: rgba(64, 158, 255, 0.14);
	border: 1px solid rgba(64, 158, 255, 0.3);
	color: #9ec9ff;
	font-size: 11px;
	font-weight: 700;
}

.steps b {
	display: block;
	font-size: 14px;
}

.steps small {
	display: block;
	margin-top: 2px;
	color: var(--pn-faint);
	font-size: 12px;
	line-height: 1.55;
}

.terms p,
.contact p {
	margin: 0 0 12px;
	color: var(--pn-muted);
	font-size: 13px;
	line-height: 1.7;
}

.terms p:last-child,
.contact p:last-child {
	margin-bottom: 0;
}

.terms b {
	color: var(--pn-text);
}

.terms a,
.contact a,
.policy-strip a,
.footer a {
	color: #8ec5ff;
	text-decoration: underline;
}

.muted {
	color: var(--pn-faint) !important;
}

.policy-strip {
	display: flex;
	flex-wrap: wrap;
	gap: 14px;
	margin-top: 30px;
	padding: 16px 18px;
	border: 1px solid var(--pn-border);
	border-radius: 12px;
	background: var(--pn-card-2);
	color: var(--pn-faint);
	font-size: 12px;
}

.policy-strip a {
	font-weight: 600;
}

.footer {
	border-top: 1px solid rgba(255, 255, 255, 0.06);
	background: #151516;
}

.footer-inner {
	display: flex;
	flex-wrap: wrap;
	justify-content: space-between;
	gap: 8px;
	max-width: 1120px;
	margin: 0 auto;
	padding: 24px;
	color: #6f7378;
	font-size: 11px;
}

@media (max-width: 880px) {
	.grid {
		grid-template-columns: 1fr;
	}

	.nav-links {
		display: none;
	}
}

@media (max-width: 560px) {
	.nav-inner,
	.wrap {
		padding-left: 18px;
		padding-right: 18px;
	}

	.brand img {
		width: 124px;
	}

	.nav-actions .btn {
		padding: 9px 14px;
		font-size: 13px;
	}

	.product {
		align-items: flex-start;
		flex-wrap: wrap;
	}

	.product-price {
		width: 100%;
		margin-left: 60px;
	}

	.actions .btn {
		font-size: 13px;
	}

	.footer-inner {
		flex-direction: column;
	}
}
</style>
