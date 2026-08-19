#!/usr/bin/env python3
"""Verify the pinned Voice-of-Janus / Echo-Pyramid runtime and calibration locks.

Git *blob* SHA-1 is used so values can be compared directly with GitHub content
blob SHAs. The verifier also checks semantic boundaries that must remain true
across larynx, embedded-runtime and physical-calibration evolution.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "config" / "the_voice_of_janus.runtime_lock.json"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def require_hex40(value: object, label: str) -> str:
    text = str(value)
    if re.fullmatch(r"[0-9a-f]{40}", text) is None:
        raise AssertionError(f"{label} must be a 40-character lowercase hex SHA: {text!r}")
    return text


def verify_local_blob(lock_section: dict[str, object], path_key: str, sha_key: str) -> None:
    relative = Path(str(lock_section[path_key]))
    expected = require_hex40(lock_section[sha_key], sha_key)
    actual = git_blob_sha(ROOT / relative)
    if actual != expected:
        raise AssertionError(
            f"runtime lock drift for {relative}: expected Git blob {expected}, actual {actual}"
        )
    print(f"LOCK OK {relative} {actual}")


def main() -> int:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    if lock.get("schema") != "janus.echo_pyramid.voice_runtime_lock.v2":
        raise AssertionError("runtime lock schema must be v2")
    if lock.get("status") != "ACTIVE_PINNED_LANGUAGE_RUNTIME_WITH_AIDAR_EUGENE_SPIRAL":
        raise AssertionError("unexpected runtime lock status")

    canonical = lock["canonical_language"]
    require_hex40(canonical["activation_blob_sha"], "activation_blob_sha")
    require_hex40(
        canonical["reference_implementation_blob_sha"],
        "reference_implementation_blob_sha",
    )
    if canonical["profile_id"] != "PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3":
        raise AssertionError("unexpected canonical Pyramid Language profile id")
    if canonical.get("semantic_content_preserved") is not True:
        raise AssertionError("canonical language must preserve semantic content")

    larynx = lock["upstream_larynx"]
    if larynx.get("larynx_is_language") is not False:
        raise AssertionError("larynx must remain distinct from Pyramid Language")
    if larynx.get("larynx_change_modifies_pyramid_parameters") is not False:
        raise AssertionError("larynx change must not modify Pyramid Language parameters")

    embedded = lock["embedded_implementation"]
    if embedded.get("revision") != "ESP32-r2":
        raise AssertionError("embedded revision must be ESP32-r2")

    verify_local_blob(embedded, "voice_contract", "voice_contract_blob_sha")
    verify_local_blob(embedded, "profile_header", "profile_header_blob_sha")
    verify_local_blob(embedded, "dsp_header", "dsp_header_blob_sha")
    verify_local_blob(embedded, "composer", "composer_blob_sha")

    profile_text = (ROOT / str(embedded["profile_header"])).read_text(encoding="utf-8")
    if "PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3/ESP32-r2" not in profile_text:
        raise AssertionError("profile header does not identify ESP32-r2")
    if "kAnchorCenterHz = 119.0f" not in profile_text:
        raise AssertionError("119 Hz anchor center missing from embedded profile")
    if "kEmbeddedDelayDamping = 0.00234256f" not in profile_text:
        raise AssertionError("time-equivalent decimated damping invariant missing")

    contract = json.loads((ROOT / str(embedded["voice_contract"])).read_text(encoding="utf-8"))
    if contract.get("version") != "2.7":
        raise AssertionError("voice contract must be physical contract v2.7")

    dsp = contract["primary_dsp"]
    if dsp.get("language_version") != canonical["profile_id"]:
        raise AssertionError("voice contract language version disagrees with runtime lock")
    if dsp.get("embedded_revision") != embedded["revision"]:
        raise AssertionError("voice contract embedded revision disagrees with runtime lock")
    if dsp.get("anchor_band_hz") != [117.0, 121.0]:
        raise AssertionError("voice contract anchor band drifted")
    if dsp.get("anchor_center_hz") != 119.0:
        raise AssertionError("voice contract anchor center drifted")

    physical_cal = contract["physical_calibration"]
    if physical_cal.get("status") != "PENDING_DEVICE_MEASUREMENT":
        raise AssertionError("voice contract physical calibration must remain pending")
    if physical_cal.get("signal_position") != "POST_PYRAMID_LANGUAGE_PRE_M5ECHOPYRAMID_WRITE":
        raise AssertionError("voice contract calibration gate moved out of post-language position")
    if physical_cal.get("measured_compensation_active") is not False:
        raise AssertionError("voice contract activated unmeasured physical compensation")
    if physical_cal.get("rule") != "CALIBRATE_THE_BODY_WITHOUT_SILENTLY_REWRITING_THE_LANGUAGE":
        raise AssertionError("voice contract calibration boundary rule missing")
    neutral = physical_cal["neutral_defaults"]
    if neutral.get("output_trim_percent") != 100:
        raise AssertionError("unmeasured output trim must remain neutral at 100 percent")
    if neutral.get("speaker_compensation_eq_enabled") is not False:
        raise AssertionError("unmeasured speaker compensation EQ must remain disabled")

    integration = contract["integration"]
    ownership = integration["mutable_state_ownership"]
    if ownership.get("owner") != "JANUS_AUDIO_PLAYBACK_TASK":
        raise AssertionError("DSP mutable state must be owned by JANUS audio task")
    if ownership.get("external_control_transport") != "PORTMUX_GUARDED_REQUEST_MAILBOX":
        raise AssertionError("external DSP controls must use the portMUX mailbox")
    if ownership.get("application_boundary") != "NEXT_PCM_BLOCK":
        raise AssertionError("external DSP controls must apply at a PCM block boundary")
    if ownership.get("usb_parser_direct_dsp_mutation") is not False:
        raise AssertionError("USB parser must not mutate DSP state directly")

    failsafe = integration["audio_budget_failsafe"]
    if failsafe.get("default_enabled") is not True:
        raise AssertionError("audio budget failsafe must be enabled by default")
    if failsafe.get("default_consecutive_block_limit") != 3:
        raise AssertionError("audio budget failsafe must trip after 3 consecutive overruns")
    if failsafe.get("priority_rule") != "AUDIO_CONTINUITY_HAS_PRIORITY_OVER_EFFECT":
        raise AssertionError("audio continuity priority invariant missing")

    lock_conformance = lock["embedded_conformance"]
    if lock_conformance.get("dsp_mutable_state_owner") != "JANUS_AUDIO_PLAYBACK_TASK":
        raise AssertionError("runtime lock does not pin audio-task DSP ownership")
    if lock_conformance.get("direct_cross_core_usb_dsp_mutation") is not False:
        raise AssertionError("runtime lock permits cross-core USB DSP mutation")

    calibration = lock["hardware_calibration"]
    if calibration.get("status") != "PENDING_DEVICE_MEASUREMENT":
        raise AssertionError("hardware calibration must remain pending until measured")
    if calibration.get("signal_position") != "POST_PYRAMID_LANGUAGE_PRE_SPEAKER":
        raise AssertionError("physical calibration must remain post-language")
    if calibration.get("measured_compensation_active") is not False:
        raise AssertionError("unmeasured physical compensation must remain disabled")
    if calibration.get("speaker_compensation_eq_enabled") is not False:
        raise AssertionError("speaker compensation EQ cannot be enabled before measurement")
    if calibration.get("language_parameter_change_requires_new_language_version") is not True:
        raise AssertionError("language retunes must require a new language version")

    verify_local_blob(calibration, "contract", "contract_blob_sha")
    verify_local_blob(calibration, "receipt_template", "receipt_template_blob_sha")

    cal_contract = json.loads((ROOT / str(calibration["contract"])).read_text(encoding="utf-8"))
    if cal_contract.get("principle") != "CALIBRATE_THE_BODY_WITHOUT_SILENTLY_REWRITING_THE_LANGUAGE":
        raise AssertionError("hardware calibration boundary principle missing")
    if cal_contract.get("language_profile") != canonical["profile_id"]:
        raise AssertionError("hardware calibration contract points to wrong language profile")
    if cal_contract["physical_calibration_parameters"]["speaker_compensation_eq"].get("status") != "DISABLED_UNTIL_MEASURED_DEVICE_RESPONSE":
        raise AssertionError("speaker compensation EQ must be measurement-gated")
    if cal_contract["versioning"].get("silent_mutation") != "FORBIDDEN":
        raise AssertionError("silent language mutation must be forbidden")

    expected_locked = {
        "anchor_band_hz",
        "anchor_center_hz",
        "anchor_q",
        "anchor_gain_db",
        "anchor_decay_s",
        "resonators_hz",
        "room_geometry_m",
        "room_decay",
        "wet",
        "dry",
    }
    if set(calibration.get("language_locked_parameters", [])) != expected_locked:
        raise AssertionError("runtime lock language-locked calibration parameter set drifted")
    if set(physical_cal.get("language_locked_parameters", [])) != expected_locked:
        raise AssertionError("voice contract language-locked calibration parameter set drifted")

    print("JANUS Echo-Pyramid runtime + calibration lock PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
