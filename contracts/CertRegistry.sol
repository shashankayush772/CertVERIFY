// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CertRegistry {
    
    // Maps certificate ID to its SHA-256 hash
    mapping(string => string) private certHashes;
    
    // Maps certificate ID to timestamp of when it was stored
    mapping(string => uint256) private certTimestamps;
    
    // Owner of the contract
    address public owner;
    
    // Events
    event CertificateStored(string certId, string hash, uint256 timestamp);
    event CertificateRevoked(string certId, uint256 timestamp);
    
    constructor() {
        owner = msg.sender;
    }
    
    // Store a certificate hash on blockchain
    function storeHash(string memory certId, string memory hash) public {
        require(bytes(certId).length > 0, "certId cannot be empty");
        require(bytes(hash).length > 0, "hash cannot be empty");
        certHashes[certId] = hash;
        certTimestamps[certId] = block.timestamp;
        emit CertificateStored(certId, hash, block.timestamp);
    }
    
    // Get a stored hash by certificate ID
    function getHash(string memory certId) public view returns (string memory) {
        return certHashes[certId];
    }
    
    // Check if a certificate exists on chain
    function certExists(string memory certId) public view returns (bool) {
        return bytes(certHashes[certId]).length > 0;
    }
    
    // Get timestamp of when certificate was stored
    function getTimestamp(string memory certId) public view returns (uint256) {
        return certTimestamps[certId];
    }
    
    // Revoke a certificate (only owner)
    function revokeHash(string memory certId) public {
        require(msg.sender == owner, "Only owner can revoke");
        require(bytes(certHashes[certId]).length > 0, "Certificate not found");
        certHashes[certId] = "REVOKED";
        emit CertificateRevoked(certId, block.timestamp);
    }
}
