import { shaderMaterial } from '@react-three/drei';
import { extend } from '@react-three/fiber';
import * as THREE from 'three';

// [AGENT NOTE]: PlasticWrapMaterial — Engine-owned overlay shader.
// Creates a frosted cling-film look: subtle Fresnel rim + thin-film iridescence.
// Applied as a transparent additive layer over the product mesh.

const vertexShader = /* glsl */`
  varying vec3 vNormal;
  varying vec3 vViewDir;
  varying vec2 vUv;

  void main() {
    vUv = uv;
    vec4 worldPos = modelMatrix * vec4(position, 1.0);
    vec3 worldNormal = normalize(mat3(modelMatrix) * normal);
    vec3 cameraWorldPos = (inverse(viewMatrix) * vec4(0.0, 0.0, 0.0, 1.0)).xyz;

    vNormal  = worldNormal;
    vViewDir = normalize(cameraWorldPos - worldPos.xyz);

    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const fragmentShader = /* glsl */`
  uniform float uTime;
  uniform float uFresnelPower;
  uniform vec3  uRimColor;
  uniform float uOpacity;

  varying vec3 vNormal;
  varying vec3 vViewDir;
  varying vec2 vUv;

  // Thin-film iridescence helper
  vec3 thinFilm(float cosTheta, float thickness) {
    float phase = thickness * cosTheta * 6.2831853;
    return 0.5 + 0.5 * vec3(
      cos(phase),
      cos(phase + 2.094),   // 2π/3
      cos(phase + 4.189)    // 4π/3
    );
  }

  void main() {
    // Fresnel: brighter where surface is perpendicular to view (edges)
    float cosTheta  = clamp(dot(vNormal, vViewDir), 0.0, 1.0);
    float fresnel   = pow(1.0 - cosTheta, uFresnelPower);

    // Thin-film shimmer that animates slowly
    float thickness = 0.4 + 0.2 * sin(uTime * 0.5 + vUv.x * 4.0);
    vec3  film      = thinFilm(cosTheta, thickness);

    // Combine: rim glow + iridescent film
    vec3  color     = mix(uRimColor, film, 0.4) * fresnel;
    float alpha     = fresnel * uOpacity;

    gl_FragColor = vec4(color, alpha);
  }
`;

// Create the Drei shaderMaterial class
const PlasticWrapMat = shaderMaterial(
  {
    uTime:         0,
    uFresnelPower: 3.5,
    uRimColor:     new THREE.Color('#a8d8ea'),   // cool icy blue tint
    uOpacity:      0.65,
  },
  vertexShader,
  fragmentShader
);

// Register with R3F so <plasticWrapMat /> works in JSX
extend({ PlasticWrapMat });

export { PlasticWrapMat };
